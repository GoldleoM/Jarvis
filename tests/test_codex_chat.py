import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, Mock, patch

from agent_runner import AppServer, CodexChat, CodexError, SECTION


class CodexTests(unittest.IsolatedAsyncioTestCase):
    async def test_resume_only_jarvis_thread_and_keep_utility_calls_temporary(self):
        server = Mock()
        server.answer = AsyncMock(return_value="A reply")
        server.section_id = AsyncMock(return_value="jarvis-section")
        server.request = AsyncMock(side_effect=[
            {"thread": {"id": "jarvis-thread"}}, {}, {},
            {"thread": {"id": "temporary-thread"}}, {},
        ])

        @asynccontextmanager
        async def connected(folder):
            self.assertEqual(folder, chat.folder)
            yield server

        chat = CodexChat(Path("Jarvis Chats").absolute())
        with patch("agent_runner.connect", connected):
            await chat.ask("First question")
            await chat.ask("Give this note a title", temporary=True)
            await chat.ask("Follow-up")
        requests = server.request.await_args_list
        self.assertEqual([call.args[0] for call in requests], [
            "thread/start", "thread/section/move", "thread/name/set", "thread/start", "thread/resume",
        ])
        self.assertEqual(requests[1].args[1], {"threadId": "jarvis-thread", "sectionId": "jarvis-section"})
        self.assertTrue(requests[3].args[1]["ephemeral"])
        self.assertEqual(requests[4].args[1]["threadId"], "jarvis-thread")
        self.assertEqual([call.args[0] for call in server.answer.await_args_list],
                         ["jarvis-thread", "temporary-thread", "jarvis-thread"])
        self.assertIsNone(CodexChat(chat.folder).thread_id)

    async def test_find_section_on_another_page_or_create_it(self):
        server = AppServer(Mock())
        server.request = AsyncMock(side_effect=[
            {"data": [{"name": "Personal", "id": "other"}], "nextCursor": "next"},
            {"data": [{"name": SECTION, "id": "existing"}]},
            {"data": []}, {"section": {"id": "created"}},
        ])
        self.assertEqual(await server.section_id(), "existing")
        self.assertEqual(await server.section_id(), "created")
        server.request.assert_awaited_with("threadSection/create", {"name": SECTION})

    async def test_only_final_message_from_the_current_turn_is_spoken(self):
        def message(thread, turn, text, phase):
            return {"method": "item/completed", "params": {"threadId": thread, "turnId": turn,
                    "item": {"type": "agentMessage", "text": text, "phase": phase}}}

        server = AppServer(Mock())
        server.send = AsyncMock()
        server.receive = AsyncMock(side_effect=[
            message("J", "T", "Early reply", "final_answer"),
            {"id": 1, "result": {"turn": {"id": "T"}}},
            message("J", "T", "Thinking aloud", "commentary"),
            message("other", "T", "Other chat", "final_answer"),
            message("J", "old", "Old turn", "final_answer"),
            {"method": "turn/completed", "params": {"threadId": "J", "turn": {"id": "T", "status": "completed"}}},
        ])
        self.assertEqual(await server.answer("J", "question"), "Early reply")

    async def test_failed_and_cancelled_turns(self):
        server = AppServer(Mock())
        server.request = AsyncMock(return_value={"turn": {"id": "T"}})
        server.receive = AsyncMock(return_value={"method": "turn/completed", "params": {
            "threadId": "J", "turn": {"id": "T", "status": "failed", "error": {"message": "Please sign in"}}}})
        with self.assertRaisesRegex(CodexError, "Please sign in"):
            await server.answer("J", "question")
        server.receive.side_effect = asyncio.CancelledError
        with self.assertRaises(asyncio.CancelledError):
            await server.answer("J", "cancel this")
        server.request.assert_awaited_with("turn/interrupt", {"threadId": "J", "turnId": "T"})
