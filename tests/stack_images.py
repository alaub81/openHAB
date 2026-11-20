"""Resolve public default images without reading local ENV files or credentials."""

import re

from lint import ROOT, dotenv, load_yaml


def stack_images():
    values = dotenv((ROOT / ".env.advanced.example").read_text())
    images = {}
    for name in ("docker-compose.yml", "docker-compose.advanced.yml"):
        services = load_yaml((ROOT / name).read_text())["services"]
        for service, config in services.items():
            image = config["image"]
            image = re.sub(r"\$\{([A-Z_]+):-([^}]+)\}", lambda m: values.get(m[1], m[2]), image)
            if "$" in image or not re.fullmatch(r"[a-zA-Z0-9./:_@-]+", image):
                raise ValueError(f"Unresolved public image: {service}")
            images[service] = image
    return images


if __name__ == "__main__":
    for service, image in stack_images().items():
        print(f"{service}={image}")
