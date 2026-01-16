# Path: core/config_gen.py
# Version: 15.4 (Core)
# Description: Умное слияние конфигураций (Deep Merge).

import copy

def deep_update(base_dict, new_dict):
    """
    Рекурсивно обновляет словарь.
    Списки перезаписываются полностью (это важно для tags_module/checkboxes_module).
    """
    for key, value in new_dict.items():
        if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
            deep_update(base_dict[key], value)
        else:
            base_dict[key] = value
    return base_dict

def resolve_config(fas_data, path_list):
    """
    Проходит по пути от main до конечного узла, накапливая настройки.
    """
    root_node = fas_data.get("category", {}).get("main", {})
    
    # Начинаем с конфига MAIN
    final_config = copy.deepcopy(root_node.get("supported_types", {}))

    cursor = root_node.get("children", {})

    for step in path_list:
        if step in cursor:
            current_node = cursor[step]
            if "supported_types" in current_node:
                new_rules = current_node["supported_types"]
                deep_update(final_config, new_rules)
            
            cursor = current_node.get("children", {})
        else:
            break
            
    return final_config

def get_next_children(fas_data, path_list):
    cursor = fas_data.get("category", {}).get("main", {}).get("children", {})
    for step in path_list:
        if step in cursor:
            cursor = cursor[step].get("children", {})
        else:
            return {}
    return cursor