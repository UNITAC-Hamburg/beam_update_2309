#!/usr/bin/env python3

import argparse
from functools import partial
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from osgeo_utils.gdal_pansharpen import gdal_pansharpen
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def pansharpen_image(ms_path, pan_directory, output_directory):
    """
    Pan-sharpens a given multispectral image using its corresponding panchromatic image.

    Parameters:
    ms_path (Path): A Path object pointing to the multispectral image file.
    pan_directory (Path): A Path object representing the directory containing panchromatic images.
    output_directory (Path): A Path object representing the directory where the pan-sharpened images will be saved.

    Returns:
    str: A message indicating the status of the pan-sharpening process for the image.
    """

    # Construct the corresponding panchromatic image filename
    pan_image_name = ms_path.name.replace("M3DS", "P3DS")

    # Full paths for the input and output images
    pan_image_paths = list(pan_directory.rglob(pan_image_name))
    if len(pan_image_paths) > 0:
        pan_image_path = pan_image_paths[0]
        output_image_path = output_directory / ms_path.name.replace("M3DS", "PS3DS")

        if not output_image_path.exists():

            # Execute the command
            gdal_pansharpen(
                pan_name=str(pan_image_path),
                spectral_names=[str(ms_path)],
                dst_filename=str(output_image_path),
            )
        else:
            return f"Pan-sharpened image already exists for {ms_path.name}, skipping."
    else:
        return f"No panchromatic match found for {ms_path.name}, skipping."


def main(ms_directory, pan_directory, output_directory):
    # List all multispectral images

    if (
        not ms_directory.exists()
        or not pan_directory.exists()
        or not any(pan_directory.rglob("*"))
    ):
        raise FileNotFoundError(
            f"The {'multispectral' if not ms_directory.exists() else 'panchromatic'} directory \
                is empty or does not exist."
        )

    # Check if output directory exists, create it if it does not
    if not output_directory.exists():
        output_directory.mkdir(parents=True)

    ms_images = []
    ms_images.extend(ms_directory.rglob("*.tif"))
    ms_images.extend(ms_directory.rglob("*.tiff"))
    ms_images.extend(ms_directory.rglob("*.TIF"))
    ms_images.extend(ms_directory.rglob("*.TIFF"))

    # Remove duplicates and select multiband images
    ms_images = list(img for img in set(ms_images) if "M3DS" in str(img))

    if not ms_images:
        raise ValueError("No multispectral images found in the specified directory.")

    partial_pansharpen_func = partial(
        pansharpen_image, pan_directory=pan_directory, output_directory=output_directory
    )

    with ProcessPoolExecutor() as executor:
        results = list(
            tqdm(executor.map(partial_pansharpen_func, ms_images), total=len(ms_images))
        )

    for result in results:
        if result is not None:
            logging.warning(result)

    logging.info("Pan-sharpening process completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pan-sharpening script.")
    parser.add_argument(
        "--mul_dir",
        type=str,
        help="Directory containing multispectral images",
        required=True,
    )
    parser.add_argument(
        "--pan_dir",
        type=str,
        help="Directory containing panchromatic images",
        required=True,
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        help="Output directory for pan-sharpened images",
        required=True,
    )

    args = parser.parse_args()

    mul_dir = Path(args.mul_dir)
    pan_dir = Path(args.pan_dir)
    output_dir = Path(args.output_dir)

    main(mul_dir, pan_dir, output_dir)
