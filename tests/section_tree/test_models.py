from src.section_tree.models import SectionTree, TreeNode


def test_tree_node_defaults():
    node = TreeNode(
        node_id="doc1::root",
        doc_id="doc1",
        title="__root__",
        block_id="",
        heading_level=0,
        depth=0,
        parent_id=None,
    )
    assert node.children == []
    assert node.page_spans == (0, 0)
    assert node.summary == ""


def test_tree_node_children_independent():
    a = TreeNode("a", "d", "A", "", 1, 1, None)
    b = TreeNode("b", "d", "B", "", 1, 1, None)
    a.children.append(TreeNode("c", "d", "C", "", 2, 2, "a"))
    assert len(b.children) == 0


def test_section_tree_fields():
    root = TreeNode("doc1::root", "doc1", "__root__", "", 0, 0, None, page_spans=(1, 10))
    tree = SectionTree(doc_id="doc1", source_file="f.pdf", root=root, total_pages=10)
    assert tree.doc_id == "doc1"
    assert tree.total_pages == 10
    assert tree.root is root
