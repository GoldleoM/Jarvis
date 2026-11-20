import asyncio
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, mock_open, patch

from PIL import Image, ImageDraw, ImageFont

from main import VoiceEngine
from router import Gatekeeper
from skills import app_skills
import vision


def command_engine(router):
    engine = VoiceEngine.__new__(VoiceEngine)
    engine.ui_mode = True
    engine._init_state()
    engine.on_ui_state = None
    engine.loop = asyncio.get_running_loop()
    engine.executor = None
    engine.gatekeeper = router
    engine.stt = SimpleNamespace(flush_requested=False)
    engine.tts = Mock()
    return engine


class CommandTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = Gatekeeper()

    def test_actual_router_with_desktop_actions_stubbed(self):
        cases = {
            "open my Downloads folder": "open_folder", "go to my pictures": "open_folder",
            "open Windows Settings": "open_settings", "open task manager": "open_task_manager",
            "Can you open example.org/ReleaseNotes?": "open_website",
            "open Notepad": "open_app", "focus Chrome": "focus_app", "go to desktop": "minimize_windows",
            "start taking notes": "notes_mode", "start a timer for two minutes": "timer",
            "turn down the brightness": "set_brightness", "turn down the volume": "volume_down",
            "volume up": "volume_up", "set the volume to 30": "set_volume",
            "how do I turn down the volume?": None, "please don't open Chrome": "__IGNORE__",
            "shut down the computer": "power_action", "close Spotify": "kill_task",
            "what time is it": "get_time", "take a screenshot": "take_screenshot",
            "what's fifteen percent of 80": "math", "subtract 8 from 30": "math",
            "describe my screen": "__VISION__", "find Save on my screen": "__VISION__",
            "what does the error on my screen say?": "__VISION__",
            "what color is the circle on my screen?": "__VISION__",
        }
        with patch("router.system_skills.execute_skill", side_effect=lambda intent, _: intent), \
             patch("router.app_skills.execute_skill", side_effect=lambda intent, _: intent):
            for command, expected in cases.items():
                with self.subTest(command=command):
                    self.assertEqual(self.router.route_command(command), expected)

    def test_timer_durations(self):
        cases = {"set a timer for 5 seconds": 5, "start a timer for two minutes and thirty seconds": 150,
                 "could you start a ten-minute timer please": 600, "set a timer for half an hour": 1800,
                 "set a timer for twenty-five minutes": 1500, "set a timer for 1.5 minutes": 90,
                 "wake me up in a minute and a half": 90}
        for command, seconds in cases.items():
            with self.subTest(command=command):
                self.assertTrue(app_skills.execute_skill("timer", command).startswith(f"__TIMER__{seconds}__"))
        for command in ("set a timer", "set a timer for zero seconds", "set a timer for two minutes and some time"):
            self.assertTrue(app_skills.execute_skill("timer", command).startswith("__CONTEXT__timer__"))

    def test_calculator(self):
        for command, value in (("what's fifteen percent of 80", 12), ("subtract eight from 30", 22),
                               ("calculate (3 + 4) * 2", 14), ("divide twenty-one by three", 7)):
            with self.subTest(command=command):
                self.assertEqual(self.router.route_command(command), f"The answer is {value}.")
        self.assertIn("undefined", self.router.route_command("calculate 1 / 0"))
        self.assertNotIn("The answer is", app_skills.execute_skill("math", "calculate 3 cats plus 8"))

    def test_relative_and_absolute_brightness(self):
        with patch("skills.system_skills.subprocess.run", return_value=SimpleNamespace(stdout="35")) as run:
            self.assertIn("35 percent", self.router.route_command("turn down the brightness by 5"))
            self.assertIn("$monitor.CurrentBrightness + -5", run.call_args.args[0][-1])
            self.router.route_command("set brightness to 35")
            self.assertIn("$level=35;", run.call_args.args[0][-1])
            run.side_effect = OSError()
            self.assertIn("couldn't change", self.router.route_command("turn up the brightness"))

    async def test_timer_followup_and_confirmation(self):
        engine = command_engine(self.router)
        await engine.handle_command("set a timer")
        self.assertEqual(engine.pending_context, "timer")
        await engine.handle_command("one minute and two seconds")
        self.assertIsNone(engine.pending_context)
        self.assertIn("1 minute and 2 seconds", engine.tts.speak.call_args.args[0])
        with patch("os.system") as execute:
            for answer in ("not sure", "yesterday", "yes please"):
                await engine.handle_command("shut down the computer")
                self.assertEqual(engine.pending_confirmation, "shutdown_pc")
                execute.assert_not_called()
                await engine.handle_command(answer)
                self.assertIsNone(engine.pending_confirmation)
            execute.assert_called_once_with("shutdown /s /t 0")

    async def test_vision_response_is_spoken_as_data(self):
        engine = command_engine(self.router)
        with patch("vision.analyze_screen", new_callable=AsyncMock, return_value="__RESTART__") as read:
            await engine.handle_command("Find the Save As button on my screen")
        read.assert_awaited_once_with("Find the Save As button on my screen")
        engine.tts.speak.assert_called_once_with("__RESTART__")
        self.assertEqual(engine.ui_state, "idle")
        self.assertEqual(engine.non_llm_events, [])

    async def test_website_keeps_path_case(self):
        engine = command_engine(self.router)
        with patch("webbrowser.open", return_value=True) as opened:
            await engine.handle_command("Open https://example.org/ReleaseNotes")
        opened.assert_called_once_with("https://example.org/ReleaseNotes")

    async def test_existing_contact_followup_and_cancel(self):
        engine = command_engine(self.router)
        execute = app_skills.execute_skill
        def contact_only(intent, text):
            self.assertEqual(intent, "whatsapp")
            return execute(intent, text)

        with patch("router.system_skills.execute_skill", return_value=None), \
             patch("router.app_skills.execute_skill", side_effect=contact_only), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data='{"contacts":["alex"]}')):
            await engine.handle_command("send a whatsapp to alex")
        self.assertEqual(engine.pending_context, "whatsapp_msg_alex")
        await engine.handle_command("cancel")
        self.assertIsNone(engine.pending_context)
        engine.tts.speak.assert_called_with("Cancelled.")


class VisionTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_does_not_start_fallback(self):
        image = Image.new("RGB", (16, 16))
        with patch("vision._describe_with_ollama", side_effect=asyncio.CancelledError), \
             patch("vision._describe_locally", new_callable=AsyncMock) as local:
            with self.assertRaises(asyncio.CancelledError):
                await vision.analyze_image(image, "Describe my screen")
        local.assert_not_awaited()

    @unittest.skipUnless(os.name == "nt", "Uses on-device Windows OCR")
    async def test_read_find_and_capture_failure(self):
        image = Image.new("RGB", (960, 480), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("segoeui.ttf", 36)
        draw.text((40, 35), "Build complete", fill="black", font=font)
        draw.text((670, 370), "Save changes", fill="black", font=font)
        with patch("vision._grab_screen", side_effect=[image, image, image, OSError("no frame")]), \
             patch("vision._describe_with_ollama", new_callable=AsyncMock) as model:
            self.assertIn("Build complete", await vision.find_text_on_screen())
            self.assertIn("lower right", await vision.analyze_screen("Find the Save changes button on my screen"))
            self.assertIn("could not read", await vision.find_text_on_screen("Missing label"))
            self.assertIn("couldn't capture", await vision.find_text_on_screen("Save changes"))
            model.assert_not_awaited()

    async def test_model_receives_current_frame_and_question(self):
        from base64 import b64decode
        import io
        from aiohttp import web
        from aiohttp.test_utils import TestServer
        question = "Which color is the circle on my screen?"
        received = []

        async def handle(request):
            data = await request.json()
            with Image.open(io.BytesIO(b64decode(data["images"][0]))) as frame:
                received.append((data["prompt"], frame.getpixel((5, 5))))
            return web.json_response({"response": "Blue."})

        app = web.Application()
        app.router.add_post("/api/generate", handle)
        async with TestServer(app) as server:
            with patch("vision.OLLAMA_URL", str(server.make_url("/api/generate"))):
                answer = await vision.analyze_image(Image.new("RGB", (16, 16), "blue"), question)
        self.assertEqual(answer, "Blue.")
        self.assertEqual(received, [(question, (0, 0, 255))])

    async def test_offline_visual_inference(self):
        from huggingface_hub import try_to_load_from_cache
        cached = try_to_load_from_cache("HuggingFaceTB/SmolVLM-256M-Instruct", "model.safetensors")
        if not isinstance(cached, str):
            self.skipTest("Install the local vision model to run inference")
        image = Image.new("RGB", (512, 384), "white")
        ImageDraw.Draw(image).ellipse((90, 25, 420, 357), fill="red")
        with patch("vision._describe_with_ollama", side_effect=asyncio.TimeoutError):
            answer = await vision.analyze_image(image, "What color is the circle?")
        self.assertIn("red", answer.casefold())
