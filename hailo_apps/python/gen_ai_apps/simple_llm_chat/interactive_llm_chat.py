"""Interactive LLM Chat - Select model and enter prompts interactively."""
import argparse
import sys
from pathlib import Path

from hailo_platform import VDevice
from hailo_platform.genai import LLM

from hailo_apps.python.core.common.defines import (
    LLM_CHAT_APP,
    SHARED_VDEVICE_GROUP_ID,
    HAILO10H_ARCH,
    RESOURCES_ROOT_PATH_DEFAULT,
    RESOURCES_MODELS_DIR_NAME,
    HAILO_FILE_EXTENSION,
)
from hailo_apps.python.core.common.hailo_logger import get_logger

# Initialize logger
logger = get_logger(__name__)


def get_downloaded_llm_models() -> list[Path]:
    """Find all downloaded LLM models (gen-ai models) in the resources directory."""
    models_dir = Path(RESOURCES_ROOT_PATH_DEFAULT) / RESOURCES_MODELS_DIR_NAME / HAILO10H_ARCH

    if not models_dir.exists():
        return []

    # Gen-AI LLM models typically have descriptive names like Qwen2.5-1.5B-Instruct
    # Filter for .hef files that look like LLM models (contain common LLM name patterns)
    llm_patterns = [
        "qwen", "llama", "mistral", "gemma", "phi", "instruct", "chat", "coder"
    ]

    models = []
    for hef_file in models_dir.glob(f"*{HAILO_FILE_EXTENSION}"):
        name_lower = hef_file.stem.lower()
        # Include if it matches any LLM pattern
        if any(pattern in name_lower for pattern in llm_patterns):
            models.append(hef_file)

    return sorted(models, key=lambda p: p.stem.lower())


def select_model(models: list[Path]) -> Path:
    """Display model selection menu and return selected model path."""
    print("\n" + "=" * 60)
    print("Available LLM Models")
    print("=" * 60)

    for i, model in enumerate(models, 1):
        print(f"  [{i}] {model.stem}")

    print("=" * 60)

    while True:
        try:
            choice = input("\nSelect model number (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                print("Exiting...")
                sys.exit(0)

            idx = int(choice) - 1
            if 0 <= idx < len(models):
                return models[idx]
            else:
                print(f"Please enter a number between 1 and {len(models)}")
        except ValueError:
            print("Please enter a valid number")


def interactive_chat(llm: LLM, system_prompt: str = "You are a helpful assistant."):
    """Run interactive chat loop."""
    print("\n" + "=" * 60)
    print("Interactive LLM Chat")
    print("=" * 60)
    print("Commands:")
    print("  /quit or /exit - Exit the chat")
    print("  /clear - Clear conversation context")
    print("  /system <prompt> - Change system prompt")
    print("=" * 60 + "\n")

    conversation = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]}
    ]

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ['/quit', '/exit']:
                print("\nGoodbye!")
                break

            if user_input.lower() == '/clear':
                llm.clear_context()
                conversation = [
                    {"role": "system", "content": [{"type": "text", "text": system_prompt}]}
                ]
                print("Context cleared.\n")
                continue

            if user_input.lower().startswith('/system '):
                new_system = user_input[8:].strip()
                if new_system:
                    system_prompt = new_system
                    llm.clear_context()
                    conversation = [
                        {"role": "system", "content": [{"type": "text", "text": system_prompt}]}
                    ]
                    print(f"System prompt updated to: {system_prompt}\n")
                else:
                    print("Please provide a system prompt.\n")
                continue

            # Add user message to conversation
            conversation.append({
                "role": "user",
                "content": [{"type": "text", "text": user_input}]
            })

            # Generate response
            print("\nAssistant: ", end="", flush=True)

            response = llm.generate_all(
                prompt=conversation,
                temperature=0.7,
                max_generated_tokens=500
            )

            # Clean up response (remove any trailing metadata)
            clean_response = response.split(". [{'type'")[0]
            print(clean_response)

            # Add assistant response to conversation
            conversation.append({
                "role": "assistant",
                "content": [{"type": "text", "text": clean_response}]
            })

            print()  # Empty line for readability

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            print(f"\nError: {e}\n")


def main():
    """Main function for Interactive LLM Chat."""
    parser = argparse.ArgumentParser(description="Interactive LLM Chat")
    parser.add_argument(
        "--hef-path",
        type=str,
        default=None,
        help="Path to HEF model file (skips model selection)"
    )
    parser.add_argument(
        "--system-prompt",
        type=str,
        default="You are a helpful assistant.",
        help="Initial system prompt for the conversation"
    )
    args = parser.parse_args()

    # Find or select model
    if args.hef_path:
        hef_path = Path(args.hef_path)
        if not hef_path.exists():
            # Try adding .hef extension
            hef_path = Path(str(args.hef_path) + HAILO_FILE_EXTENSION)
        if not hef_path.exists():
            logger.error(f"Model file not found: {args.hef_path}")
            sys.exit(1)
    else:
        # Find downloaded models
        models = get_downloaded_llm_models()

        if not models:
            print("\nNo LLM models found in the resources directory.")
            print(f"Expected location: {RESOURCES_ROOT_PATH_DEFAULT}/models/{HAILO10H_ARCH}/")
            print("\nTo download models, run:")
            print("  hailo-download-resources --arch hailo10h")
            sys.exit(1)

        if len(models) == 1:
            hef_path = models[0]
            print(f"\nUsing only available model: {hef_path.stem}")
        else:
            hef_path = select_model(models)

    print(f"\nSelected model: {hef_path.stem}")

    vdevice = None
    llm = None

    try:
        print("\n[1/2] Initializing Hailo device...")
        params = VDevice.create_params()
        params.group_id = SHARED_VDEVICE_GROUP_ID
        vdevice = VDevice(params)
        print("Hailo device initialized")

        print("[2/2] Loading LLM model...")
        llm = LLM(vdevice, str(hef_path))
        print("Model loaded successfully")

        # Start interactive chat
        interactive_chat(llm, args.system_prompt)

    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        sys.exit(1)

    finally:
        if llm:
            try:
                llm.clear_context()
                llm.release()
            except Exception as e:
                logger.warning(f"Error releasing LLM: {e}")

        if vdevice:
            try:
                vdevice.release()
            except Exception as e:
                logger.warning(f"Error releasing VDevice: {e}")


if __name__ == "__main__":
    main()
