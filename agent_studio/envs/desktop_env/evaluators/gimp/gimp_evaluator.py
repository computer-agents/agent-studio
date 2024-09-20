import logging
import os

import cv2
import numpy as np
from PIL import Image, ImageStat
from skimage.metrics import structural_similarity as ssim

from agent_studio.config import Config
from agent_studio.envs.desktop_env.evaluators.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
)

config = Config()
logger = logging.getLogger(__name__)


def structure_check_by_ssim(img1, img2, threshold=0.9):
    """Check if two images are approximately the same by SSIM"""
    similarity = ssim(
        np.array(img1), np.array(img2), multichannel=True, channel_axis=-1
    )
    print("SSIM: ", similarity)
    return similarity >= threshold


def measure_saturation(hsv_image):
    """Measure the average saturation of an image"""
    # Split into H, S, V channels
    _, s, _ = hsv_image.split()
    # Convert the saturation channel to a numpy array
    s_array = np.array(s)
    # Calculate the average saturation
    avg_saturation = np.mean(s_array)
    return avg_saturation


def calculate_brightness(image):
    """Calculate the average brightness of an image"""
    grayscale = image.convert("L")
    stat = ImageStat.Stat(grayscale)
    return stat.mean[0]


def normalize_brightness(image, target_brightness):
    """Normalize the brightness of an image to a target brightness in [0, 1]"""
    current_brightness = calculate_brightness(image)
    factor = target_brightness / current_brightness

    # Apply a point transform to each pixel
    def point_transform(x):
        return min(255, max(0, int(x * factor)))

    return image.point(point_transform)


def calculate_contrast(image):
    """Calculate the contrast of an image as the standard deviation of the pixel
    values."""
    pixels = np.asarray(image, dtype=np.float32)
    return np.std(pixels)


def calculate_image_sharpness(image_path):
    # Load the image in grayscale
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    # Apply the Laplacian operator
    laplacian = cv2.Laplacian(image, cv2.CV_64F)
    # Calculate the variance
    variance = np.var(laplacian)
    return variance


def structure_check_by_mse(img1, img2, threshold=0.03):
    """Check if two images are approximately the same by MSE"""
    mse = np.mean(
        (
            np.array(img1, dtype=np.float32) / 255
            - np.array(img2, dtype=np.float32) / 255
        )
        ** 2
    )
    structure_same = True if mse < threshold else False
    print("MSE: ", mse)
    return structure_same


class GIMPEvaluator(Evaluator):
    name: str = "gimp"

    @evaluation_handler("check_brightness_decrease_and_structure_sim")
    def check_brightness_decrease_and_structure_sim(self, src_path, tgt_path):
        """
        Check the brightness of src is lower than tgt and the structures are similar.
        """
        if not os.path.exists(src_path):
            raise FeedbackException(f"The source image {src_path} does not exist.")
        if not os.path.exists(tgt_path):
            raise FeedbackException(f"The target image {tgt_path} does not exist.")
        img_src = Image.open(src_path)
        img_tgt = Image.open(tgt_path)

        # Brightness comparison
        brightness_src = calculate_brightness(img_src)
        brightness_tgt = calculate_brightness(img_tgt)
        brightness_reduced = brightness_tgt > brightness_src

        # Normalize and compare images
        target_brightness = 128
        img_src_normalized = normalize_brightness(img_src, target_brightness)
        img_tgt_normalized = normalize_brightness(img_tgt, target_brightness)

        structure_same = structure_check_by_mse(img_src_normalized, img_tgt_normalized)
        if not (brightness_reduced and structure_same):
            raise FeedbackException(
                "The brightness of the source image is not lower than the target image."
            )

    @evaluation_handler("check_saturation_increase_and_structure_sim")
    def check_saturation_increase_and_structure_sim(self, src_path, tgt_path):
        """
        Check the saturation of src is higher than tgt and the structures are similar.
        """
        if not os.path.exists(src_path):
            raise FeedbackException(f"The source image {src_path} does not exist.")
        if not os.path.exists(tgt_path):
            raise FeedbackException(f"The target image {tgt_path} does not exist.")
        img_src = Image.open(src_path)
        hsv_img_src = img_src.convert("HSV")
        img_tgt = Image.open(tgt_path)
        hsv_img_tgt = img_tgt.convert("HSV")

        # Saturation comparison
        src_saturation = measure_saturation(hsv_img_src)
        tgt_saturation = measure_saturation(hsv_img_tgt)

        saturation_increased = tgt_saturation < src_saturation

        # Structure comparison
        h1, s1, v1 = hsv_img_src.split()
        h2, s2, v2 = hsv_img_tgt.split()
        h_same = structure_check_by_ssim(h1, h2)
        v_same = structure_check_by_ssim(v1, v2)
        if h_same and v_same:
            structure_same = True
        else:
            structure_same = False

        if not (saturation_increased and structure_same):
            raise FeedbackException(
                "The saturation of the source image is not higher than the target image."  # noqa: E501
            )

    @evaluation_handler("check_file_exists_and_structure_sim")
    def check_file_exists_and_structure_sim(self, src_path, tgt_path):
        """
        Check if the image has been exported to the desktop.
        """
        # Check if the file exists
        export_file_exists = os.path.isfile(src_path)
        if not export_file_exists:
            raise FeedbackException("The file has not been exported to the desktop.")

        # Check whether the target image is the same as the source image
        img_src = Image.open(src_path)
        img_tgt = Image.open(tgt_path)
        structure_same = structure_check_by_ssim(img_src, img_tgt)

        if not structure_same:
            raise FeedbackException(
                "The exported image is not the same as the source image."
            )

    @evaluation_handler("check_triangle_position")
    def check_triangle_position(self, tgt_path):
        """
        Check if the triangle is in the middle of the image.
        """
        if not os.path.exists(tgt_path):
            raise FeedbackException(f"The target image {tgt_path} does not exist.")
        # Load the image
        img = Image.open(tgt_path)
        img_array = np.array(img)

        # We assume the triangle is a different color from the background
        # Find the unique colors
        unique_colors, counts = np.unique(
            img_array.reshape(-1, img_array.shape[2]), axis=0, return_counts=True
        )
        unique_colors_sorted = unique_colors[np.argsort(counts)]

        # Assuming the background is the most common color and the triangle is a different color  # noqa: E501
        triangle_color = unique_colors_sorted[1]

        # Create a mask where the triangle pixels are True
        triangle_mask = np.all(img_array == triangle_color, axis=2)

        # Get the coordinates of the triangle pixels
        triangle_coords = np.argwhere(triangle_mask)

        # Calculate the centroid of the triangle
        centroid = triangle_coords.mean(axis=0)

        # Check if the centroid is approximately in the middle of the image
        image_center = np.array(img_array.shape[:2]) / 2

        # We will consider the triangle to be in the middle if the centroid is within 5% of the image's center  # noqa: E501
        tolerance = 0.05 * np.array(img_array.shape[:2])
        middle = np.all(np.abs(centroid - image_center) < tolerance)

        if not bool(middle):
            raise FeedbackException("The triangle is not in the middle of the image.")

    @evaluation_handler("check_structure_sim")
    def check_structure_sim(self, src_path, tgt_path):
        """
        Check if the structure of the two images are similar.
        """
        if not os.path.exists(src_path):
            raise FeedbackException(f"The source image {src_path} does not exist.")
        if not os.path.exists(tgt_path):
            raise FeedbackException(f"The target image {tgt_path} does not exist.")
        img_src = Image.open(src_path)
        img_tgt = Image.open(tgt_path)
        structure_same = structure_check_by_ssim(img_src, img_tgt)
        if not structure_same:
            raise FeedbackException("The structures of the two images are not similar.")

    @evaluation_handler("check_structure_sim_resized")
    def check_structure_sim_resized(self, src_path, tgt_path):
        """
        Check if the structure of the two images are similar after resizing.
        """
        if not os.path.exists(src_path):
            raise FeedbackException(f"The source image {src_path} does not exist.")
        if not os.path.exists(tgt_path):
            raise FeedbackException(f"The target image {tgt_path} does not exist.")
        img_src = Image.open(src_path)
        img_tgt = Image.open(tgt_path)

        # Resize the images to the same size
        img_src = img_src.resize(img_tgt.size)

        # Check if the structure is similar
        structure_same = structure_check_by_ssim(img_src, img_tgt)
        if not structure_same:
            raise FeedbackException("The structures of the two images are not similar.")

    @evaluation_handler("check_contrast_increase_and_structure_sim")
    def check_contrast_increase_and_structure_sim(src_path, tgt_path):
        """
        Check if the src image has higher contrast than the tgt image and the structures are similar.  # noqa: E501
        """
        if not os.path.exists(src_path):
            raise FeedbackException(f"The source image {src_path} does not exist.")
        if not os.path.exists(tgt_path):
            raise FeedbackException(f"The target image {tgt_path} does not exist.")
        # Load images
        source_image = Image.open(src_path)
        target_image = Image.open(tgt_path)

        # Calculate contrast
        source_contrast = calculate_contrast(source_image)
        target_contrast = calculate_contrast(target_image)
        higher_contrast = target_contrast < source_contrast

        # Check structure
        structure_same = structure_check_by_ssim(
            source_image, target_image, threshold=0.65
        )

        if not (higher_contrast and structure_same):
            raise FeedbackException(
                "The source image does not have higher contrast than the target image."
            )

    @evaluation_handler("check_image_size")
    def check_image_size(self, src_path, rule):
        """
        Check if the size of the src image is correct.
        """
        # Load the image
        if not os.path.exists(src_path):
            raise FeedbackException(f"The source image {src_path} does not exist.")
        img = Image.open(src_path)

        # Check the size
        if rule.get("height", None) is not None:
            height_same = img.size[1] == rule["height"]
        else:
            height_same = True
        if rule.get("width", None) is not None:
            width_same = img.size[0] == rule["width"]
        else:
            width_same = True

        if not (height_same and width_same):
            raise FeedbackException("The size of the image is not correct.")

    @evaluation_handler("check_image_file_size")
    def check_image_file_size(self, src_path, rule):
        """
        Check if the size of the src image within 500KB
        """
        # Check if the file exists
        if not os.path.isfile(src_path):
            raise FeedbackException("The file does not exist.")
        # Check the size
        file_size = os.path.getsize(src_path)
        if file_size >= rule["max_size"]:
            raise FeedbackException("The file size is too large.")

    @evaluation_handler("check_palette_and_structure_sim")
    def check_palette_and_structure_sim(self, src_path: str, tgt_path: str):
        """
        Check if the src image is palette-based and the structure of the two images are similar.  # noqa: E501
        """
        # Check if the source image is palette-based
        if not os.path.exists(src_path):
            raise FeedbackException(f"The source image {src_path} does not exist.")
        if not os.path.exists(tgt_path):
            raise FeedbackException(f"The target image {tgt_path} does not exist.")
        source_image = Image.open(src_path)
        palette_based = source_image.mode == "P"

        # Check structure
        target_image = Image.open(tgt_path)
        source_image = source_image.convert("RGB")
        structure_same = structure_check_by_ssim(source_image, target_image)
        if not (palette_based and structure_same):
            raise FeedbackException(
                "The source image is not palette-based or the structures are not similar."  # noqa: E501
            )

    @evaluation_handler("check_textbox_on_leftside")
    def check_textbox_on_leftside(self, src_path):
        """
        Check if the textbox is on the left side of the image.
        """
        if not os.path.exists(src_path):
            raise FeedbackException(f"The source image {src_path} does not exist.")
        source_image = Image.open(src_path)
        gray_image = source_image.convert("L")
        width, height = source_image.size

        # Find the bounds of the black text
        left_most_dark_pixel = width  # Start with the farthest possible left position
        for y in range(height):
            for x in range(width):
                # If the pixel is dark, consider it as part of the text
                if gray_image.getpixel((x, y)) < 128:  # Arbitrary threshold for "dark"
                    left_most_dark_pixel = min(left_most_dark_pixel, x)
                    break  # Stop after finding the first dark pixel in this row

        # Here we define "almost" on the left side as being within the left 5% of the image  # noqa: E501
        if left_most_dark_pixel >= width * 0.05:
            raise FeedbackException("The textbox is not on the left side of the image.")

    @evaluation_handler("check_image_mirror")
    def check_image_mirror(self, src_path, tgt_path):
        """
        Check if the image is mirrored.
        """
        if not os.path.exists(src_path):
            raise FeedbackException(f"The source image {src_path} does not exist.")
        if not os.path.exists(tgt_path):
            raise FeedbackException(f"The target image {tgt_path} does not exist.")
        # Load images
        source_image = Image.open(src_path)
        target_image = Image.open(tgt_path)

        # Check if the image is mirrored
        transposed_image = source_image.transpose(Image.FLIP_LEFT_RIGHT)
        # Use 0.99 because the image may not be exactly mirrored by gimp
        mirrored = structure_check_by_ssim(transposed_image, target_image, 0.99)
        if not mirrored:
            raise FeedbackException("The image is not mirrored.")

    @evaluation_handler("check_green_background")
    def check_green_background(self, src_path: str, tgt_path: str):
        """Check if the background of the source image is green."""
        # Load images
        if not os.path.exists(src_path):
            raise FeedbackException(f"The source image {src_path} does not exist.")
        if not os.path.exists(tgt_path):
            raise FeedbackException(f"The target image {tgt_path} does not exist.")
        source_image = Image.open(src_path)
        target_image = Image.open(tgt_path)

        source_pixels = np.array(source_image)
        target_pixels = np.array(target_image)

        for x in range(target_image.width):
            for y in range(target_image.height):
                # Identify background pixel in target image (not black)
                if tuple(target_pixels[x, y][:3]) != (0, 0, 0):
                    # Check if corresponding pixel in source image is green
                    # Here, "green" means more green than red or blue
                    r, g, b = source_pixels[x, y][:3]
                    if not (g > r and g > b):
                        raise FeedbackException(
                            f"Background pixel at ({x}, {y}) in source image is not green"  # noqa: E501
                        )
