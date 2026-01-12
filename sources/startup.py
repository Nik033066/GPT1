import os
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# Set matplotlib config dir to avoid permission issues
os.environ['MPLCONFIGDIR'] = '/tmp/mplconfig'
if not os.path.exists('/tmp/mplconfig'):
    os.makedirs('/tmp/mplconfig', exist_ok=True)

from sources.llm_provider import Provider
from sources.interaction import Interaction
from sources.agents import CasualAgent, CoderAgent, FileAgent, PlannerAgent, BrowserAgent
from sources.browser import Browser, create_driver

def is_running_in_docker():
    """Detect if code is running inside a Docker container."""
    # Method 1: Check for .dockerenv file
    if os.path.exists('/.dockerenv'):
        return True
    
    # Method 2: Check cgroup
    try:
        with open('/proc/1/cgroup', 'r') as f:
            return 'docker' in f.read()
    except:
        pass
    
    return False

def initialize_system(config, logger):
    stealth_mode = config.getboolean('BROWSER', 'stealth_mode')
    personality_folder = "custom" if config.getboolean('MAIN', 'custom_personality') else "base"
    languages = config["MAIN"]["languages"].split(' ')
    
    # Force headless mode in Docker containers
    headless = config.getboolean('BROWSER', 'headless_browser')
    if is_running_in_docker() and not headless:
        # Print prominent warning to console (visible in docker-compose output)
        print("\n" + "*" * 70)
        print("*** WARNING: Detected Docker environment - forcing headless_browser=True ***")
        print("*** INFO: To see the browser, run 'python cli.py' on your host machine ***")
        print("*" * 70 + "\n")
        
        # Flush to ensure it's displayed immediately
        sys.stdout.flush()
        
        # Also log to file
        logger.warning("Detected Docker environment - forcing headless_browser=True")
        logger.info("To see the browser, run 'python cli.py' on your host machine instead")
        
        headless = True
    
    provider = Provider(
        provider_name=config["MAIN"]["provider_name"],
        model=config["MAIN"]["provider_model"],
        server_address=config["MAIN"]["provider_server_address"],
        is_local=config.getboolean('MAIN', 'is_local')
    )
    logger.info(f"Provider initialized: {provider.provider_name} ({provider.model})")

    # Try to initialize browser, fallback to None if it fails
    browser = None
    try:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            lambda: Browser(
                create_driver(headless=headless, stealth_mode=stealth_mode, lang=languages[0]),
                anticaptcha_manual_install=stealth_mode,
            )
        )
        browser = future.result(timeout=20)
        executor.shutdown(wait=False, cancel_futures=True)
        logger.info("Browser initialized")
    except FuturesTimeoutError:
        logger.warning("Browser initialization timed out")
        logger.info("Running without browser - BrowserAgent will use search-only mode")
    except Exception as e:
        logger.warning(f"Browser initialization failed: {e}")
        logger.info("Running without browser - BrowserAgent will use search-only mode")

    agents = [
        CasualAgent(
            name=config["MAIN"]["agent_name"],
            prompt_path=f"prompts/{personality_folder}/casual_agent.txt",
            provider=provider, verbose=False
        ),
        CoderAgent(
            name="coder",
            prompt_path=f"prompts/{personality_folder}/coder_agent.txt",
            provider=provider, verbose=False
        ),
        FileAgent(
            name="File Agent",
            prompt_path=f"prompts/{personality_folder}/file_agent.txt",
            provider=provider, verbose=False
        ),
        BrowserAgent(
            name="Browser",
            prompt_path=f"prompts/{personality_folder}/browser_agent.txt",
            provider=provider, verbose=False, browser=browser
        ),
        PlannerAgent(
            name="Planner",
            prompt_path=f"prompts/{personality_folder}/planner_agent.txt",
            provider=provider, verbose=False, browser=browser
        )
    ]
    logger.info("Agents initialized")

    interaction = Interaction(
        agents,
        tts_enabled=config.getboolean('MAIN', 'speak'),
        stt_enabled=config.getboolean('MAIN', 'listen'),
        recover_last_session=config.getboolean('MAIN', 'recover_last_session'),
        langs=languages
    )
    logger.info("Interaction initialized")
    return interaction
