"""Local image inference worker. stdin carries a JSON question line and a PNG."""
import io
import json
import sys

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor


MODEL = "HuggingFaceTB/SmolVLM-256M-Instruct"


def describe(image, question):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoProcessor.from_pretrained(MODEL, local_files_only=True)
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL, local_files_only=True, torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    ).to(device).eval()
    image.thumbnail((1024, 1024))
    content = [{"type": "image"}, {"type": "text", "text": question}]
    prompt = processor.apply_chat_template([{"role": "user", "content": content}], add_generation_prompt=True)
    inputs = processor(text=prompt, images=[image], return_tensors="pt").to(model.device, model.dtype)
    with torch.inference_mode():
        output = model.generate(**inputs, do_sample=False, max_new_tokens=80)
    return processor.decode(output[0, inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()


if __name__ == "__main__":
    question = json.loads(sys.stdin.buffer.readline())
    with Image.open(io.BytesIO(sys.stdin.buffer.read())) as image:
        print(json.dumps(describe(image, question)))
