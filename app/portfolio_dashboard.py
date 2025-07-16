from nicegui import ui
from decimal import Decimal
from typing import Optional, List
from app.portfolio_service import portfolio_service
from app.models import HoldingCreate, HoldingUpdate, AssetType, PortfolioCreate


class PortfolioDashboard:
    def __init__(self):
        self.current_portfolio_id: Optional[int] = None
        self.holdings_table: Optional[ui.table] = None
        self.summary_cards: List[ui.card] = []
        self.refresh_timer: Optional[ui.timer] = None
        self.auto_refresh = True

    def create_portfolio_selector(self) -> ui.select:
        """Create portfolio selector dropdown"""
        portfolios = portfolio_service.get_all_portfolios()

        # Create options for dropdown
        options = []
        for portfolio in portfolios:
            options.append({"label": portfolio.name, "value": portfolio.id})

        # Add "Create New" option
        options.append({"label": "+ Create New Portfolio", "value": "create_new"})

        selector = ui.select(options=options, value=self.current_portfolio_id, label="Select Portfolio").classes("w-64")

        def on_portfolio_change(e):
            if e.value == "create_new":
                # Create task for async call
                import asyncio

                asyncio.create_task(self.show_create_portfolio_dialog())
            else:
                self.current_portfolio_id = e.value
                self.refresh_dashboard()

        selector.on("update:model-value", on_portfolio_change)
        return selector

    async def show_create_portfolio_dialog(self):
        """Show dialog to create new portfolio"""
        with ui.dialog() as dialog, ui.card():
            ui.label("Create New Portfolio").classes("text-lg font-bold mb-4")

            name_input = ui.input(label="Portfolio Name", placeholder="e.g., My Investment Portfolio").classes(
                "w-full mb-2"
            )

            description_input = (
                ui.textarea(label="Description", placeholder="Optional description")
                .classes("w-full mb-4")
                .props("rows=3")
            )

            with ui.row().classes("gap-2 justify-end"):
                ui.button("Cancel", on_click=dialog.close).props("outline")
                ui.button(
                    "Create", on_click=lambda: self.create_portfolio(dialog, name_input.value, description_input.value)
                ).classes("bg-primary text-white")

        result = await dialog
        return result

    def create_portfolio(self, dialog, name: str, description: str):
        """Create new portfolio"""
        if not name.strip():
            ui.notify("Portfolio name is required", type="negative")
            return

        try:
            portfolio_data = PortfolioCreate(name=name.strip(), description=description.strip())
            portfolio = portfolio_service.create_portfolio(portfolio_data)

            self.current_portfolio_id = portfolio.id
            ui.notify(f'Portfolio "{portfolio.name}" created successfully!', type="positive")
            dialog.close()

            # Refresh the entire page to update portfolio selector
            ui.navigate.reload()

        except Exception as e:
            ui.notify(f"Error creating portfolio: {str(e)}", type="negative")

    def create_summary_section(self):
        """Create the portfolio summary section"""
        with ui.row().classes("gap-4 w-full mb-6") as summary_row:
            # Summary cards will be populated by refresh_summary
            pass

        self.summary_row = summary_row
        return summary_row

    async def refresh_summary(self):
        """Refresh the portfolio summary section"""
        if self.current_portfolio_id is None:
            return

        try:
            summary = await portfolio_service.get_portfolio_summary(self.current_portfolio_id)
            if summary is None:
                return

            # Clear existing summary cards
            self.summary_row.clear()

            with self.summary_row:
                # Total Value Card
                with ui.card().classes("p-6 bg-white shadow-lg rounded-xl hover:shadow-xl transition-shadow"):
                    ui.label("Total Portfolio Value").classes("text-sm text-gray-500 uppercase tracking-wider")
                    ui.label(f"${summary.total_current_value:,.2f}").classes("text-3xl font-bold text-gray-800 mt-2")
                    change_color = "text-green-500" if summary.total_absolute_return >= 0 else "text-red-500"
                    ui.label(f"${summary.total_absolute_return:+,.2f}").classes(f"text-sm {change_color} mt-1")

                # Total Cost Card
                with ui.card().classes("p-6 bg-white shadow-lg rounded-xl hover:shadow-xl transition-shadow"):
                    ui.label("Total Investment").classes("text-sm text-gray-500 uppercase tracking-wider")
                    ui.label(f"${summary.total_cost:,.2f}").classes("text-3xl font-bold text-gray-800 mt-2")
                    ui.label(f"{summary.total_holdings} holdings").classes("text-sm text-gray-500 mt-1")

                # ROI Card
                with ui.card().classes("p-6 bg-white shadow-lg rounded-xl hover:shadow-xl transition-shadow"):
                    ui.label("Return on Investment").classes("text-sm text-gray-500 uppercase tracking-wider")
                    roi_color = "text-green-500" if summary.total_percentage_return >= 0 else "text-red-500"
                    ui.label(f"{summary.total_percentage_return:+.2f}%").classes(f"text-3xl font-bold {roi_color} mt-2")
                    ui.label(f"Updated: {summary.last_updated.strftime('%H:%M')}").classes("text-sm text-gray-500 mt-1")

                # Best/Worst Performer Card
                with ui.card().classes("p-6 bg-white shadow-lg rounded-xl hover:shadow-xl transition-shadow"):
                    ui.label("Performance").classes("text-sm text-gray-500 uppercase tracking-wider")
                    if summary.best_performer:
                        ui.label(f"↗ {summary.best_performer}").classes("text-lg font-bold text-green-500 mt-2")
                    if summary.worst_performer:
                        ui.label(f"↘ {summary.worst_performer}").classes("text-lg font-bold text-red-500")
                    if not summary.best_performer and not summary.worst_performer:
                        ui.label("No data").classes("text-lg font-bold text-gray-500 mt-2")

        except Exception as e:
            ui.notify(f"Error refreshing summary: {str(e)}", type="negative")

    def create_holdings_table(self):
        """Create the holdings table"""
        columns = [
            {"name": "symbol", "label": "Symbol", "field": "symbol", "align": "left"},
            {"name": "asset_type", "label": "Type", "field": "asset_type", "align": "left"},
            {"name": "quantity", "label": "Quantity", "field": "quantity", "align": "right"},
            {"name": "purchase_price", "label": "Purchase Price", "field": "purchase_price", "align": "right"},
            {"name": "current_price", "label": "Current Price", "field": "current_price", "align": "right"},
            {"name": "total_cost", "label": "Total Cost", "field": "total_cost", "align": "right"},
            {"name": "current_value", "label": "Current Value", "field": "current_value", "align": "right"},
            {"name": "absolute_return", "label": "Return ($)", "field": "absolute_return", "align": "right"},
            {"name": "percentage_return", "label": "Return (%)", "field": "percentage_return", "align": "right"},
            {"name": "actions", "label": "Actions", "field": "actions", "align": "center"},
        ]

        self.holdings_table = ui.table(columns=columns, rows=[], row_key="id").classes("w-full")

        # Add custom styling for the table
        self.holdings_table.add_slot(
            "body-cell-current_price",
            """
            <q-td :props="props" :class="props.row.current_price ? '' : 'text-gray-400'">
                {{ props.row.current_price ? '$' + parseFloat(props.row.current_price).toFixed(2) : 'Loading...' }}
            </q-td>
        """,
        )

        self.holdings_table.add_slot(
            "body-cell-total_cost",
            """
            <q-td :props="props">
                ${{ parseFloat(props.row.total_cost).toFixed(2) }}
            </q-td>
        """,
        )

        self.holdings_table.add_slot(
            "body-cell-current_value",
            """
            <q-td :props="props" :class="props.row.current_value ? '' : 'text-gray-400'">
                {{ props.row.current_value ? '$' + parseFloat(props.row.current_value).toFixed(2) : 'N/A' }}
            </q-td>
        """,
        )

        self.holdings_table.add_slot(
            "body-cell-absolute_return",
            """
            <q-td :props="props" :class="props.row.absolute_return ? (parseFloat(props.row.absolute_return) >= 0 ? 'text-green-600' : 'text-red-600') : 'text-gray-400'">
                {{ props.row.absolute_return ? (parseFloat(props.row.absolute_return) >= 0 ? '+' : '') + '$' + parseFloat(props.row.absolute_return).toFixed(2) : 'N/A' }}
            </q-td>
        """,
        )

        self.holdings_table.add_slot(
            "body-cell-percentage_return",
            """
            <q-td :props="props" :class="props.row.percentage_return ? (parseFloat(props.row.percentage_return) >= 0 ? 'text-green-600' : 'text-red-600') : 'text-gray-400'">
                {{ props.row.percentage_return ? (parseFloat(props.row.percentage_return) >= 0 ? '+' : '') + parseFloat(props.row.percentage_return).toFixed(2) + '%' : 'N/A' }}
            </q-td>
        """,
        )

        self.holdings_table.add_slot(
            "body-cell-actions",
            """
            <q-td :props="props">
                <q-btn flat color="primary" icon="edit" size="sm" @click="$parent.$emit('edit-holding', props.row.id)" />
                <q-btn flat color="negative" icon="delete" size="sm" @click="$parent.$emit('delete-holding', props.row.id)" />
            </q-td>
        """,
        )

        self.holdings_table.on("edit-holding", self.edit_holding)
        self.holdings_table.on("delete-holding", self.delete_holding)

        return self.holdings_table

    async def refresh_holdings_table(self):
        """Refresh the holdings table with current data"""
        if self.current_portfolio_id is None or self.holdings_table is None:
            return

        try:
            holdings = await portfolio_service.get_holdings_with_metrics(self.current_portfolio_id)

            # Convert holdings to table rows
            rows = []
            for holding in holdings:
                row = {
                    "id": holding.id,
                    "symbol": holding.symbol,
                    "asset_type": holding.asset_type.value.title(),
                    "quantity": f"{holding.quantity:,.8f}".rstrip("0").rstrip("."),
                    "purchase_price": f"${holding.purchase_price:.2f}",
                    "current_price": float(holding.current_price) if holding.current_price else None,
                    "total_cost": float(holding.total_cost) if holding.total_cost else 0,
                    "current_value": float(holding.current_value) if holding.current_value else None,
                    "absolute_return": float(holding.absolute_return) if holding.absolute_return else None,
                    "percentage_return": float(holding.percentage_return) if holding.percentage_return else None,
                }
                rows.append(row)

            self.holdings_table.rows = rows

        except Exception as e:
            ui.notify(f"Error refreshing holdings: {str(e)}", type="negative")

    async def show_add_holding_dialog(self):
        """Show dialog to add new holding"""
        if self.current_portfolio_id is None:
            ui.notify("Please select a portfolio first", type="warning")
            return

        with ui.dialog() as dialog, ui.card():
            ui.label("Add New Holding").classes("text-lg font-bold mb-4")

            with ui.row().classes("gap-4 w-full"):
                symbol_input = ui.input(label="Symbol", placeholder="e.g., AAPL, BTC-USD").classes("flex-1")

                asset_type_select = ui.select(
                    options=[{"label": "Stock", "value": "stock"}, {"label": "Cryptocurrency", "value": "crypto"}],
                    value="stock",
                    label="Asset Type",
                ).classes("flex-1")

            with ui.row().classes("gap-4 w-full"):
                quantity_input = ui.number(label="Quantity", value=1, min=0.00000001, step=0.1).classes("flex-1")

                purchase_price_input = ui.number(label="Purchase Price ($)", value=0, min=0.01, step=0.01).classes(
                    "flex-1"
                )

            notes_input = (
                ui.textarea(label="Notes (Optional)", placeholder="Additional notes about this holding")
                .classes("w-full mb-4")
                .props("rows=2")
            )

            with ui.row().classes("gap-2 justify-end"):
                ui.button("Cancel", on_click=dialog.close).props("outline")
                ui.button(
                    "Add Holding",
                    on_click=lambda: self.add_holding(
                        dialog,
                        symbol_input.value,
                        asset_type_select.value,
                        quantity_input.value,
                        purchase_price_input.value,
                        notes_input.value,
                    ),
                ).classes("bg-primary text-white")

        await dialog

    def add_holding(
        self, dialog, symbol: str, asset_type: str | None, quantity: float, purchase_price: float, notes: str
    ):
        """Add new holding to portfolio"""
        if not symbol or not symbol.strip():
            ui.notify("Symbol is required", type="negative")
            return

        if quantity <= 0:
            ui.notify("Quantity must be greater than 0", type="negative")
            return

        if purchase_price <= 0:
            ui.notify("Purchase price must be greater than 0", type="negative")
            return

        if self.current_portfolio_id is None:
            ui.notify("Please select a portfolio first", type="negative")
            return

        try:
            holding_data = HoldingCreate(
                portfolio_id=self.current_portfolio_id,
                symbol=symbol.strip().upper(),
                asset_type=AssetType(asset_type or "stock"),
                quantity=Decimal(str(quantity)),
                purchase_price=Decimal(str(purchase_price)),
                notes=notes.strip() if notes else "",
            )

            portfolio_service.add_holding(holding_data)
            ui.notify(f"Holding {symbol.upper()} added successfully!", type="positive")
            dialog.close()

            # Refresh the dashboard
            self.refresh_dashboard()

        except Exception as e:
            ui.notify(f"Error adding holding: {str(e)}", type="negative")

    async def edit_holding(self, e):
        """Edit an existing holding"""
        holding_id = e.args
        holding = portfolio_service.get_holding(holding_id)

        if holding is None:
            ui.notify("Holding not found", type="negative")
            return

        with ui.dialog() as dialog, ui.card():
            ui.label("Edit Holding").classes("text-lg font-bold mb-4")

            with ui.row().classes("gap-4 w-full"):
                symbol_input = ui.input(label="Symbol", value=holding.symbol).classes("flex-1")

                asset_type_select = ui.select(
                    options=[{"label": "Stock", "value": "stock"}, {"label": "Cryptocurrency", "value": "crypto"}],
                    value=holding.asset_type.value,
                    label="Asset Type",
                ).classes("flex-1")

            with ui.row().classes("gap-4 w-full"):
                quantity_input = ui.number(
                    label="Quantity", value=float(holding.quantity), min=0.00000001, step=0.1
                ).classes("flex-1")

                purchase_price_input = ui.number(
                    label="Purchase Price ($)", value=float(holding.purchase_price), min=0.01, step=0.01
                ).classes("flex-1")

            notes_input = (
                ui.textarea(label="Notes (Optional)", value=holding.notes).classes("w-full mb-4").props("rows=2")
            )

            with ui.row().classes("gap-2 justify-end"):
                ui.button("Cancel", on_click=dialog.close).props("outline")
                ui.button(
                    "Update Holding",
                    on_click=lambda: self.update_holding(
                        dialog,
                        holding_id,
                        symbol_input.value,
                        asset_type_select.value,
                        quantity_input.value,
                        purchase_price_input.value,
                        notes_input.value,
                    ),
                ).classes("bg-primary text-white")

        await dialog

    def update_holding(
        self,
        dialog,
        holding_id: int,
        symbol: str,
        asset_type: str | None,
        quantity: float,
        purchase_price: float,
        notes: str,
    ):
        """Update existing holding"""
        if not symbol or not symbol.strip():
            ui.notify("Symbol is required", type="negative")
            return

        if quantity <= 0:
            ui.notify("Quantity must be greater than 0", type="negative")
            return

        if purchase_price <= 0:
            ui.notify("Purchase price must be greater than 0", type="negative")
            return

        try:
            holding_data = HoldingUpdate(
                symbol=symbol.strip().upper(),
                asset_type=AssetType(asset_type or "stock"),
                quantity=Decimal(str(quantity)),
                purchase_price=Decimal(str(purchase_price)),
                notes=notes.strip() if notes else "",
            )

            portfolio_service.update_holding(holding_id, holding_data)
            ui.notify("Holding updated successfully!", type="positive")
            dialog.close()

            # Refresh the dashboard
            self.refresh_dashboard()

        except Exception as e:
            ui.notify(f"Error updating holding: {str(e)}", type="negative")

    async def delete_holding(self, e):
        """Delete a holding with confirmation"""
        holding_id = e.args
        holding = portfolio_service.get_holding(holding_id)

        if holding is None:
            ui.notify("Holding not found", type="negative")
            return

        with ui.dialog() as dialog, ui.card():
            ui.label("Confirm Delete").classes("text-lg font-bold mb-4")
            ui.label(f"Are you sure you want to delete the holding for {holding.symbol}?").classes("mb-4")

            with ui.row().classes("gap-2 justify-end"):
                ui.button("Cancel", on_click=dialog.close).props("outline")
                ui.button("Delete", on_click=lambda: self.confirm_delete_holding(dialog, holding_id)).classes(
                    "bg-red-500 text-white"
                )

        await dialog

    def confirm_delete_holding(self, dialog, holding_id: int):
        """Confirm deletion of holding"""
        try:
            portfolio_service.delete_holding(holding_id)
            ui.notify("Holding deleted successfully!", type="positive")
            dialog.close()

            # Refresh the dashboard
            self.refresh_dashboard()

        except Exception as e:
            ui.notify(f"Error deleting holding: {str(e)}", type="negative")

    def refresh_dashboard(self):
        """Refresh the entire dashboard"""
        if self.current_portfolio_id is None:
            return

        # Schedule async refresh
        ui.run_javascript("""
            setTimeout(() => {
                emitEvent('refresh-dashboard');
            }, 100);
        """)

    async def handle_refresh_dashboard(self):
        """Handle dashboard refresh event"""
        await self.refresh_summary()
        await self.refresh_holdings_table()

    def setup_auto_refresh(self):
        """Setup automatic refresh timer"""

        def toggle_auto_refresh():
            if self.auto_refresh:
                if self.refresh_timer:
                    self.refresh_timer.deactivate()
                    self.refresh_timer = None
                self.auto_refresh = False
            else:
                self.refresh_timer = ui.timer(30, self.handle_refresh_dashboard)  # Refresh every 30 seconds
                self.auto_refresh = True

        # Start with auto-refresh enabled
        self.refresh_timer = ui.timer(30, self.handle_refresh_dashboard)

        return toggle_auto_refresh


def create():
    """Create the portfolio dashboard module"""
    dashboard = PortfolioDashboard()

    @ui.page("/")
    async def portfolio_page():
        # Apply modern color theme
        ui.colors(
            primary="#2563eb",
            secondary="#64748b",
            accent="#10b981",
            positive="#10b981",
            negative="#ef4444",
            warning="#f59e0b",
            info="#3b82f6",
        )

        # Header
        with ui.row().classes("w-full items-center justify-between mb-6 p-4 bg-white shadow-sm"):
            ui.label("📊 Investment Portfolio Tracker").classes("text-2xl font-bold text-primary")

            with ui.row().classes("gap-4 items-center"):
                # Portfolio selector
                portfolio_selector = dashboard.create_portfolio_selector()

                # Auto-refresh toggle
                toggle_auto_refresh = dashboard.setup_auto_refresh()
                refresh_button = ui.button(
                    "Auto-Refresh: ON",
                    on_click=lambda: (
                        toggle_auto_refresh(),
                        refresh_button.set_text("Auto-Refresh: ON" if dashboard.auto_refresh else "Auto-Refresh: OFF"),
                    ),
                ).classes("bg-secondary text-white")

                # Manual refresh button
                ui.button("Refresh Now", on_click=dashboard.handle_refresh_dashboard).classes(
                    "bg-primary text-white"
                ).props("icon=refresh")

        # Main content area
        with ui.column().classes("w-full max-w-7xl mx-auto p-4"):
            # Summary section
            dashboard.create_summary_section()

            # Holdings section
            with ui.card().classes("w-full p-6 shadow-lg"):
                with ui.row().classes("w-full items-center justify-between mb-4"):
                    ui.label("Holdings").classes("text-xl font-bold")
                    ui.button("Add Holding", on_click=dashboard.show_add_holding_dialog).classes(
                        "bg-primary text-white"
                    ).props("icon=add")

                # Holdings table
                dashboard.create_holdings_table()

        # Setup event handlers
        ui.on("refresh-dashboard", dashboard.handle_refresh_dashboard)

        # Initial load
        await dashboard.handle_refresh_dashboard()

        # Set up initial portfolio if none selected
        if dashboard.current_portfolio_id is None:
            portfolios = portfolio_service.get_all_portfolios()
            if portfolios:
                dashboard.current_portfolio_id = portfolios[0].id
                portfolio_selector.set_value(portfolios[0].id)
                await dashboard.handle_refresh_dashboard()
