import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
from PIL import Image

def compare_images(img1_path, img2_path):
    img1 = Image.open(img1_path).convert('L')
    img2 = Image.open(img2_path).convert('L')

    if img1.size != img2.size:
        img2 = img2.resize(img1.size)

    img1_np = np.array(img1)
    img2_np = np.array(img2)

    ssim_index, diff = ssim(img1_np, img2_np, full=True)

    hist1 = cv2.calcHist([img1_np], [0], None, [256], [0, 256])
    hist2 = cv2.calcHist([img2_np], [0], None, [256], [0, 256])
    hist_comparison = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

    diff_pixels = np.sum(img1_np != img2_np)
    total_pixels = img1_np.size
    pixel_diff_percentage = (diff_pixels / total_pixels) * 100

    diff_image = (diff * 255).astype(np.uint8)
    diff_image_path = 'diff_image.png'
    cv2.imwrite(diff_image_path, diff_image)

    if pixel_diff_percentage > 20:
        _, thresholded_diff = cv2.threshold(diff_image, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresholded_diff, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        img1_color = cv2.cvtColor(img1_np, cv2.COLOR_GRAY2BGR)

        for contour in contours:
            if cv2.contourArea(contour) > 10:
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(img1_color, (x, y), (x + w, y + h), (0, 0, 255), 2)

        highlighted_img1_path = 'highlighted_Diff_img.png'
        cv2.imwrite(highlighted_img1_path, img1_color)

    return ssim_index, hist_comparison, pixel_diff_percentage