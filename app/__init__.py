from flask import Flask
from .config import Config

def create_app():
    # Adjust template_folder to be relative to the running script or explicitly set
    # Assuming run.py is in the root and templates is in the root
    app = Flask(__name__, template_folder='../templates')
    app.config.from_object(Config)

    # Configure Logging
    import logging
    import sys
    
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
        stream=sys.stdout
    )

    from .routes import main_bp
    app.register_blueprint(main_bp)

    from .translations import TRANSLATIONS
    from flask import request

    def get_locale():
        # 1. Check cookie
        lang = request.cookies.get('lang')
        if lang in TRANSLATIONS:
            return lang
        
        # 2. Check Accept-Language header
        match = request.accept_languages.best_match(TRANSLATIONS.keys())
        if match:
            return match
            
        return 'en'

    @app.context_processor
    def inject_translate():
        def translate(key):
            locale = get_locale()
            return TRANSLATIONS.get(locale, TRANSLATIONS['en']).get(key, key)
        return dict(_=translate, get_locale=get_locale)

    return app
