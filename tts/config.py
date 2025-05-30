import os
import yaml

config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")

with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
