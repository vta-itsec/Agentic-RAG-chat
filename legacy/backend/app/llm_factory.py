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
    print(f"API Key loaded: {api_key[:15]}..." if api_key else "API Key: MISSING!")
    print(f"Base URL: {selected_provider['base_url']}")

    # OpenRouter yêu cầu thêm headers
    default_headers = {}
    if "openrouter" in selected_provider["name"].lower():
        default_headers = {
            "HTTP-Referer": "https://github.com/vta-itsec/Agentic-RAG-chat",
            "X-Title": "Enterprise RAG Chat"
        }
        print(f"Added OpenRouter headers: {default_headers}")

    return ChatOpenAI(
        base_url=selected_provider["base_url"],
        api_key=api_key,
        model=model_name,
        streaming=True,
        temperature=0.7,
        default_headers=default_headers
    )