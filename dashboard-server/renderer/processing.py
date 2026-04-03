import io
from PIL import Image
from config.ink import InkDisplayConfig


class ImageProcessor:
    def __init__(self, ink: InkDisplayConfig):
        self._ink = ink

    def process(self, input_bytes: bytes) -> io.BytesIO:
        img = Image.open(io.BytesIO(input_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")

        palette_img = Image.new("P", (1, 1))
        palette_data = []
        for i in range(self._ink.colors):
            val = int(i * 255 / (self._ink.colors - 1))
            palette_data.extend((val, val, val))
        palette_data.extend([0] * (768 - len(palette_data)))
        palette_img.putpalette(palette_data)

        dither = Image.Dither.NONE if not self._ink.dither else Image.Dither.FLOYDSTEINBERG
        img_quantized = img.quantize(palette=palette_img, dither=dither)
        final_img = img_quantized.convert("L")

        output = io.BytesIO()
        final_img.save(output, format=self._ink.format.upper(), optimize=True)
        output.seek(0)
        return output
