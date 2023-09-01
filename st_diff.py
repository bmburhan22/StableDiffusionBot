w, h = 100, 100
W, H = 200, 200
steps = 20
upscaler_model = "Nearest"
checkpoint = "meinapastel_v6Pastel.safetensors"
# model = "/models/LDSR"
url = "http://127.0.0.1:7860"

payload = {
    "steps": steps,
    "width": w,
    "height": h,
    "batch_size": 3,
    # "model": model,
    "override_settings": {"sd_model_checkpoint": checkpoint},
}

payload_upscale = {
    "resize_mode": 1,  # 0 for multiplier mode
    "show_extras_results": False,
    "gfpgan_visibility": 0,
    "codeformer_visibility": 0,
    "codeformer_weight": 0,
    # "upscaling_resize": 2, # resize multiplier
    "upscaling_resize_w": W,
    "upscaling_resize_h": H,
    "upscaling_crop": False,
    "upscaler_1": upscaler_model,
    "upscaler_2": "None",
    "extras_upscaler_2_visibility": 0,
    "upscale_first": False,
}

import requests
import io
import logging
import base64
import json
from PIL import Image
import discord
from discord.ui import View
from discord.ext import commands
from discord import File
from dotenv import dotenv_values


def get_image_file(image):
    if image:
        image_binary = Image.open(io.BytesIO(base64.b64decode(image.split(",", 1)[0])))
    else:
        image_binary = Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    with io.BytesIO() as image_stream:
        image_binary.save(image_stream, "PNG")
        image_stream.seek(0)
        return File(image_stream, f"image.png")


def get_collage(images):
    image_objects = [
        Image.open(io.BytesIO(base64.b64decode(image.split(",", 1)[0])))
        for image in images
    ]
    total_width = sum([img.width for img in image_objects])
    max_height = max([img.height for img in image_objects])
    collage = Image.new("RGB", (total_width, max_height))

    x_offset = 0
    for img in image_objects:
        collage.paste(img, (x_offset, 0))
        x_offset += img.width

    with io.BytesIO() as image_stream:
        collage.save(image_stream, "PNG")
        image_stream.seek(0)
        return File(image_stream, f"image.png")


def upscale(image):
    upscale_image = requests.post(
        url=f"{url}/sdapi/v1/extra-single-image",
        json=payload_upscale | {"image": image},
    ).json()
    return get_image_file(upscale_image["image"])


def generate_from_data(img_data, index):
    regenpayload = payload.copy()
    # regenpayload = {}
    img_info = json.loads(img_data["info"])
    regenpayload["batch_size"] = 1
    regenpayload["width"] = W
    regenpayload["height"] = H
    # regenpayload["steps"] = 50
    regenpayload["cfg_scale"] = 10
    regenpayload["init_images"] = [img_data["images"][index]]
    regenpayload["seed"] = img_info["all_seeds"][index]
    # regenpayload["subseed"] = img_info["all_subseeds"][index]
    regenpayload["prompt"] = img_info["all_prompts"][index]
    # regenpayload['sd_model_hash'] = img_info['sd_model_hash']
    # regenpayload['sampler_name'] = img_info['sampler_name']
    image = requests.post(url=f"{url}/sdapi/v1/img2img", json=regenpayload).json()
    return get_image_file(image["images"][0])


class Buttons(View):
    def __init__(self, interaction, images):
        super().__init__()
        self.timeout = None
        self.interaction = interaction
        self.images = images

    @discord.ui.button(label="Variation 1", row=0)
    async def button_1(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self.send_image(0, 0)

    @discord.ui.button(label="Variation 2", row=0)
    async def button_2(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self.send_image(0, 1)

    @discord.ui.button(label="Variation 3", row=0)
    async def button_3(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self.send_image(0, 2)

    @discord.ui.button(label="Upscale 1", row=1)
    async def button_4(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self.send_image(1, 0)

    @discord.ui.button(label="Upscale 2", row=1)
    async def button_5(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self.send_image(1, 1)

    @discord.ui.button(label="Upscale 3", row=1)
    async def button_6(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self.send_image(1, 2)

    async def send_image(self, f, index):
        prompt = self.images["parameters"]["prompt"]
        if f == 0:
            await self.interaction.channel.send(
                content=f"**{prompt}**\nVariation image {index + 1}:",
                file=generate_from_data(self.images, index),
            )
        else:
            await self.interaction.channel.send(
                content=f"**{prompt}**\nUpscaled image {index + 1}",
                file=upscale(self.images["images"][index]),
            )


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)

intents = discord.Intents.all()
config = dotenv_values("config.env")
BOT_TOKEN = config["BOT_TOKEN"]
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print("Bot is up!")
    try:
        synced = await bot.tree.sync()
        logging.debug(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logging.debug(f"Sync failed : {e}")


@bot.tree.command(name="generate", description="Generate Image")
async def generate(interaction: discord.Interaction, prompt: str):
    await interaction.response.send_message("processing...")
    print(f"Generating image with prompt: {prompt}")
    images = requests.post(
        url=f"{url}/sdapi/v1/txt2img", json=payload | {"prompt": prompt}
    ).json()
    # json.dump(images, open("o.json", "w", encoding="utf-8"))

    await interaction.channel.send(
        # content="\t".join([str(s) for s in json.loads(images["info"])["all_seeds"]]),
        content=f"**{prompt}**",
        view=Buttons(interaction, images),
        file=get_collage(images["images"]),
    )


bot.run(BOT_TOKEN)
