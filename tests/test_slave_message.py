from xml.etree import ElementTree as ETree

from efb_wechat_slave.slave_message import SlaveMessageManager


def test_slave_message_get_node_text():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <root>
        <item>
            <child>Text</child>
        </item>
        <emptyItem/>
    </root>
    """

    root = ETree.fromstring(xml)

    assert SlaveMessageManager.get_node_text(root, "./item/child", "") == "Text"
    assert SlaveMessageManager.get_node_text(root, "./item/non_existing", "fallback") == "fallback"
    assert SlaveMessageManager.get_node_text(root, "./emptyItem", "fallback") == "fallback"
