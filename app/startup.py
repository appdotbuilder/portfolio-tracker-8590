from app.database import create_tables
from nicegui import app
import app.portfolio_dashboard


def startup() -> None:
    # this function is called before the first request
    create_tables()

    # Register dashboard module
    app.portfolio_dashboard.create()
