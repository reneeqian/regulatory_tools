from collections import defaultdict

import yaml


class YamlRequirementProvider:

    def __init__(self, yaml_path):
        self.tag_to_ids = self._load(yaml_path)

    def _load(self, path):
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        mapping = defaultdict(list)

        for req in data.get("requirements", []):
            req_id = req.get("id")
            tags = req.get("tags", [])

            for tag in tags:
                mapping[tag].append(req_id)

        return dict(mapping)

    def get_ids(self, tag: str) -> list[str]:
        return self.tag_to_ids.get(tag, [])
