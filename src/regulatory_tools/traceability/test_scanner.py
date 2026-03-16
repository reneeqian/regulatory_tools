from pathlib import Path
import ast


def collect_requirement_markers(test_root: Path, project_root: Path = None):
    """
    Scan pytest files and collect requirement markers.

    Returns:
        dict[str, list[str]]
        { requirement_id: [test_node_ids...] }
    """
    
    if project_root is None:
        project_root = test_root

    requirement_map = {}

    for test_file in test_root.rglob("test_*.py"):
        module = ast.parse(test_file.read_text())

        for node in module.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            test_name = node.name

            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if (
                        isinstance(decorator.func, ast.Attribute)
                        and decorator.func.attr == "requirement"
                    ):

                        for arg in decorator.args:
                            req_id = arg.value
                            node_id = f"{test_file.relative_to(project_root)}::{test_name}"
                            requirement_map.setdefault(req_id, []).append(node_id)

    return requirement_map