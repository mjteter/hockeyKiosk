# from io import BytesIO
# from PIL import Image
#
# import os
# os.environ['path'] += r';C:\Program Files\UniConvertor-2.0rc5\dlls'
#
# import cairosvg
#
#
#
# for raw_pic in os.listdir('resources/logos_raw'):
#     out = BytesIO()
#     cairosvg.svg2png(url='resources/logos_raw/' + raw_pic, write_to=out)
#     image = Image.open(out)
#     image.save('resources/logos/' + raw_pic.split('.')[0] + '.png')

from PIL import Image

image = Image.open('resources/logos/PHI_dark.png')

test1 = image.resize((177, 118), Image.LANCZOS)
test2 = image.resize((177, 118), Image.BILINEAR)

test1.save('resources/test1.png')
test2.save('resources/test2.png')
