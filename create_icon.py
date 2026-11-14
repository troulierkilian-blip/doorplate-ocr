"""Create the application icon from vector-like drawing instructions."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
root=Path(__file__).resolve().parent
assets=root/'assets';assets.mkdir(exist_ok=True)
im=Image.new('RGBA',(512,512),(0,0,0,0));d=ImageDraw.Draw(im)
d.rounded_rectangle((8,8,504,504),radius=110,fill='#3267EE')
d.rounded_rectangle((85,83,427,429),radius=42,fill='#2456D6',outline='#FFFFFF',width=16)
d.line((131,131,379,131),fill='#9AB9FF',width=8)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',225)
d.text((256,262),'号',font=font,fill='white',anchor='mm')
d.ellipse((115,386,130,401),fill='#FFFFFF');d.ellipse((382,386,397,401),fill='#FFFFFF')
im=im.resize((256,256),Image.Resampling.LANCZOS)
im.save(assets/'app.png');im.save(assets/'app.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(assets/'app.ico')
