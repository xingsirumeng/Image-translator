import os
import sys
from pathlib import Path
import requests
import base64
import json
import time
from dotenv import load_dotenv, dotenv_values


def get_project_root():
    """获取项目根目录"""
    # 尝试从当前文件路径推导
    current_file = Path(__file__).resolve()

    # 如果当前文件在src目录中，则根目录是父目录
    if "src" in current_file.parts:
        return current_file.parents[1]  # 上两级目录

    # 否则使用包含.git的目录作为根目录
    for path in [current_file.parent, *current_file.parents]:
        if (path / ".git").exists():
            return path

    # 最后使用当前工作目录
    return Path.cwd()


def load_config():
    """加载或创建配置文件"""
    PROJECT_ROOT = get_project_root()
    ENV_FILE = PROJECT_ROOT / "api-data.env"

    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"环境文件路径: {ENV_FILE}")

    if ENV_FILE.exists():
        print(f"找到环境文件: {ENV_FILE}")
        return dotenv_values(ENV_FILE)
    else:
        print(f"未找到环境文件，将在根目录创建: {ENV_FILE}")

        # 获取用户输入
        print("\n请提供以下API密钥 (输入后将保存到本地文件):")
        baidu_api_key = input("百度OCR API Key: ").strip()
        baidu_secret_key = input("百度OCR Secret Key: ").strip()
        deepseek_api_key = input("DeepSeek API Key: ").strip()

        # 确保目录存在
        ENV_FILE.parent.mkdir(parents=True, exist_ok=True)

        # 保存到文件
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f"BAIDU_API_KEY={baidu_api_key}\n")
            f.write(f"BAIDU_SECRET_KEY={baidu_secret_key}\n")
            f.write(f"DEEPSEEK_API_KEY={deepseek_api_key}\n")

        print(f"\n配置已保存到 {ENV_FILE}")
        # print("请确保将此文件添加到.gitignore避免泄露")

        return {
            "BAIDU_API_KEY": baidu_api_key,
            "BAIDU_SECRET_KEY": baidu_secret_key,
            "DEEPSEEK_API_KEY": deepseek_api_key
        }


# ... 其他函数保持不变 ...


def get_baidu_ocr_token(api_key, secret_key):
    """获取百度OCR的访问令牌"""
    url = (f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret="
           f"{secret_key}")
    response = requests.post(url)
    return response.json().get("access_token")


def baidu_ocr(image_path, access_token):
    """使用百度OCR识别图片中的文字"""
    try:
        with open(image_path, "rb") as image_file:
            base64_data = base64.b64encode(image_file.read()).decode()

        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"image": base64_data}

        response = requests.post(url, headers=headers, data=data)
        result = response.json()

        if "words_result" in result:
            text_list = [res["words"] for res in result["words_result"]]
            return "\n".join(text_list)
        else:
            error_msg = result.get("error_msg", "未知错误")
            raise Exception(f"OCR识别失败: {error_msg} (错误码: {result.get('error_code', '未知')}")
    except FileNotFoundError:
        raise Exception(f"图片文件不存在: {image_path}")
    except Exception as e:
        raise Exception(f"OCR处理错误: {str(e)}")


def deepseek_translate(text, api_key, target_lang="中文"):
    """使用DeepSeek API进行文本翻译"""
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        prompt = (
            f"请将以下内容准确翻译成{target_lang}，保持原始格式不变。"
            f"文本内容：\n\n{text}\n\n"
            "要求："
            "\n1. 只返回翻译结果，不要添加额外说明"
            # "\n2. 自动识别源语言"
            # "\n3. 保持原始文本格式（换行、段落等）"
        )

        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 4000
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result = response.json()

        if "choices" in result:
            return result["choices"][0]["message"]["content"].strip()
        else:
            error_msg = result.get("error", {}).get("message", "未知错误")
            error_code = result.get("error", {}).get("code", "未知")
            raise Exception(f"翻译失败 [{error_code}]: {error_msg}")
    except requests.exceptions.Timeout:
        raise Exception("翻译请求超时，请重试")
    except Exception as e:
        raise Exception(f"翻译处理错误: {str(e)}")


def main():
    try:
        # 安全警告
        print("安全提示: API密钥将保存到本地 .env 文件")
        print("请勿分享此文件或将其上传到公开仓库\n")

        # 加载配置
        config = load_config()

        # 用户输入
        print("\n图片翻译工具")
        image_path = input("请输入图片路径: ").strip()
        target_lang = input("目标语言(默认中文): ").strip() or "中文"

        # 执行流程
        print("\n正在获取百度OCR访问令牌...")
        baidu_token = get_baidu_ocr_token(
            config["BAIDU_API_KEY"],
            config["BAIDU_SECRET_KEY"]
        )

        print("正在进行文字识别...")
        ocr_text = baidu_ocr(image_path, baidu_token)
        print(f"\n识别结果:\n{ocr_text}")

        print("\n正在翻译文本...")
        start_time = time.time()
        translation = deepseek_translate(
            ocr_text,
            config["DEEPSEEK_API_KEY"],
            target_lang
        )
        elapsed = time.time() - start_time

        print(f"\n翻译完成 ({elapsed:.2f}秒):\n{translation}")

        # 询问是否保存翻译结果
        save_option = input("\n是否保存翻译结果到文件? (y/n): ").lower()
        if save_option == "y":
            output_path = input("输出文件名(默认: translation.txt): ") or "translation.txt"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"原始文本:\n{ocr_text}\n\n")
                f.write(f"翻译结果({target_lang}):\n{translation}")
            print(f"结果已保存到 {output_path}")

    except Exception as e:
        print(f"\n 错误: {str(e)}")
        print("请检查: 1) API密钥是否正确 2) 网络连接 3) 图片路径")


if __name__ == "__main__":
    main()
