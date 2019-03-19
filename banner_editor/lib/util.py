import os
import shutil
import string

from enum import Enum
from PIL import Image


def delete_contents(folder):
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(e)


class PictureSize(Enum):
    course_icon = (256, 256)
    consumer_icon = (512, 512)


def image_resize(path, img_name, resized_name, size):
    image = Image.open(os.path.join(path, img_name))
    image = image.resize(size.value, Image.NEAREST)
    image.save(os.path.join(path, resized_name))
