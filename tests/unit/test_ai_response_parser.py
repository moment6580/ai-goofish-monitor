import pytest

from src.services.ai_response_parser import (
    extract_ai_response_content,
    parse_ai_response_json,
    EmptyAIResponseError,
)


def test_parse_ai_response_json_uses_first_object_when_multiple_json_objects_are_concatenated():
    content = """```json
{"is_recommended": true, "reason": "first"}
{"is_recommended": false, "reason": "second"}
```"""

    result = parse_ai_response_json(content)

    assert result == {"is_recommended": True, "reason": "first"}


def test_parse_ai_response_json_extracts_json_from_wrapped_text():
    content = """分析结果如下：

```json
{"is_recommended": true, "reason": "wrapped"}
```

请按第一份结果处理。"""

    result = parse_ai_response_json(content)

    assert result == {"is_recommended": True, "reason": "wrapped"}


def test_parse_ai_response_json_raises_when_no_json_exists():
    with pytest.raises(ValueError):
        parse_ai_response_json("没有任何 JSON 内容")


def test_extract_ai_response_content_with_none_content_but_valid_reasoning_content():
    """当 content 为 None 但 reasoning_content 有值时，应该成功提取 reasoning_content 的内容"""
    # 创建 mock 对象模拟 OpenAI 风格的响应
    message = type('Message', (), {
        'content': None,
        'reasoning_content': '这是推理内容'
    })()
    choice = type('Choice', (), {'message': message})()
    response = type('Response', (), {'choices': [choice]})()

    result = extract_ai_response_content(response)

    assert result == '这是推理内容'


def test_extract_ai_response_content_raises_when_content_and_reasoning_content_are_empty():
    """当 content 和 reasoning_content 都为空时，应该抛出 EmptyAIResponseError"""
    # 创建 mock 对象
    message = type('Message', (), {
        'content': None,
        'reasoning_content': None
    })()
    choice = type('Choice', (), {'message': message})()
    response = type('Response', (), {'choices': [choice]})()

    with pytest.raises(EmptyAIResponseError):
        extract_ai_response_content(response)


def test_parse_ai_response_json_accepts_python_literal_single_quotes():
    """兼容模型输出的单引号 Python 风格伪 JSON（如智谱等模型偶发）。"""
    content = "{'is_recommended': True, 'reason': 'single-quoted', 'risk_tags': [], 'criteria_analysis': {'seller_type': '个人'}}"

    result = parse_ai_response_json(content)

    assert result["is_recommended"] is True
    assert result["reason"] == "single-quoted"
    assert result["criteria_analysis"]["seller_type"] == "个人"


def test_parse_ai_response_json_prefers_standard_json_over_literal():
    content = '{"is_recommended": false, "reason": "normal"}'
    assert parse_ai_response_json(content) == {"is_recommended": False, "reason": "normal"}


def test_parse_ai_response_json_still_raises_for_unparseable_python_literal():
    with pytest.raises(ValueError):
        parse_ai_response_json("{'broken': , 'reason': }")


def test_validate_ai_response_format_allows_missing_prompt_version():
    from src.ai_handler import validate_ai_response_format

    payload = {
        "is_recommended": True,
        "reason": "ok",
        "risk_tags": [],
        "criteria_analysis": {"seller_type": "个人"},
    }
    assert validate_ai_response_format(payload) is True

    # 缺少真正必需的业务字段仍需失败
    assert validate_ai_response_format({"is_recommended": True, "reason": "x"}) is False
