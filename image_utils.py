import os
from PIL import Image, ImageChops
import imagehash

def calculate_image_hash(img_path):
    img = Image.open(img_path)
    return imagehash.average_hash(img)

def compare_images_hash(img1_path, img2_path):
    hash1 = calculate_image_hash(img1_path)
    hash2 = calculate_image_hash(img2_path)
    return hash1 != hash2  # Returns True if images are different

def compare_images(self, img1_path, img2_path):
        img1 = Image.open(img1_path)
        img2 = Image.open(img2_path)

        diff = ImageChops.difference(img1, img2)
        if diff.getbbox():
            return True  # Images are different
        return False  # Images are the same
