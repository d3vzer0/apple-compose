from typing import Any

import yaml

from apple_compose.errors import ComposeValidationError

MAX_COMPOSE_FILE_BYTES = 1024 * 1024


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> Any:
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ComposeValidationError(f"duplicate key in Compose file: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)
