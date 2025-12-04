import os
import yaml
from langchain_openai import ChatOpenAI

# Load config khi khởi động app
def load_providers():
    with open("providers.yaml", "r") as f:
        data = yaml.safe_load(f)
    return data["providers"]

PROVIDERS_CONFIG = load_providers()

def get_llm_client(model_name: str):
    """
    Hàm này nhận vào tên model (VD: 'gpt-4o', 'deepseek-chat')
    và trả về ChatOpenAI client được cấu hình đúng URL/Key.
    """
    selected_provider = None
    
    # Logic tìm provider phù hợp
    for provider in PROVIDERS_CONFIG:
        # 1. Check khớp chính xác tên model
        if "models" in provider and model_name in provider["models"]:
            selected_provider = provider
            break
        # 2. Check theo tiền tố (VD: gpt-*, local-*)
        if "prefix" in provider and model_name.startswith(provider["prefix"]):
            selected_provider = provider
            break
    
    # Fallback: Nếu không tìm thấy, dùng OpenAI mặc định hoặc báo lỗi
    if not selected_provider:
        # Bạn có thể chọn 1 provider mặc định ở đây
        selected_provider = PROVIDERS_CONFIG[0] 

    # Lấy API Key từ biến môi trường
    api_key = os.getenv(selected_provider["api_key_env"], "cannot_find_key")
    
    print(f"Routing model '{model_name}' to provider: {selected_provider['name']}")

    return ChatOpenAI(
        base_url=selected_provider["base_url"],
        api_key=api_key,
        model=model_name,
        streaming=True,
        temperature=0.7
    )