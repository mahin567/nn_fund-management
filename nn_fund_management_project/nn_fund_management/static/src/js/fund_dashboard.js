/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onMounted, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class FundDashboard extends Component {
    static template = "fund_management.DashboardTemplate";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.chartRef = useRef("incomeChart");
        this.projectChartRef = useRef("projectChart");

        this.state = useState({
            loading: true,
            data: null,
        });

        onMounted(async () => {
            await this._loadData();
        });
    }

    async _loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("fund.dashboard", "get_dashboard_data", []);
            this.state.data = data;
            this.state.loading = false;
            // charts render after next tick
            setTimeout(() => this._renderCharts(), 50);
        } catch (e) {
            console.error("Fund Dashboard load error:", e);
            this.state.loading = false;
        }
    }

    async _reload() {
        await this._loadData();
    }

    _renderCharts() {
        const data = this.state.data;
        if (!data) return;

        if (typeof Chart === "undefined") {
            console.error(
                "[nn_fund_management] Chart.js is not loaded. " +
                "Make sure /nn_fund_management/static/lib/chartjs/chart.umd.min.js " +
                "exists and is listed BEFORE the module script in assets.xml."
            );
            return;
        }

        // Monthly incoming funds sparkline
        const incomeEl = this.chartRef.el;
        if (incomeEl && data.monthly_incoming && data.monthly_incoming.length) {
            if (this._incomeChart) this._incomeChart.destroy();
            const ctx = incomeEl.getContext("2d");
            this._incomeChart = new Chart(ctx, {
                type: "bar",
                data: {
                    labels: data.monthly_incoming.map(r => r.month),
                    datasets: [{
                        label: "Incoming Funds",
                        data: data.monthly_incoming.map(r => r.total),
                        backgroundColor: "rgba(99,102,241,0.7)",
                        borderRadius: 4,
                    }],
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: { y: { ticks: { callback: v => this._fmtShort(v, data) } } },
                },
            });
        }

        // Top projects horizontal bar
        const projEl = this.projectChartRef.el;
        if (projEl && data.top_projects && data.top_projects.length) {
            if (this._projectChart) this._projectChart.destroy();
            const ctx2 = projEl.getContext("2d");
            this._projectChart = new Chart(ctx2, {
                type: "bar",
                data: {
                    labels: data.top_projects.map(p => p.name),
                    datasets: [
                        {
                            label: "Available",
                            data: data.top_projects.map(p => p.available),
                            backgroundColor: "rgba(34,197,94,0.75)",
                        },
                        {
                            label: "Spent",
                            data: data.top_projects.map(p => p.spent),
                            backgroundColor: "rgba(239,68,68,0.75)",
                        },
                    ],
                },
                options: {
                    indexAxis: "y",
                    responsive: true,
                    plugins: { legend: { position: "bottom" } },
                    scales: { x: { ticks: { callback: v => this._fmtShort(v, data) } } },
                },
            });
        }
    }

    _fmtShort(value, data) {
        const sym = (data && data.currency_symbol) || "";
        if (value >= 1000000) return sym + (value / 1000000).toFixed(1) + "M";
        if (value >= 1000) return sym + (value / 1000).toFixed(0) + "K";
        return sym + value;
    }

    fmt(value) {
        const data = this.state.data;
        if (!data) return value;
        const sym = data.currency_symbol || "";
        const pos = data.currency_position;
        const formatted = new Intl.NumberFormat().format(Math.round(value));
        return pos === "before" ? sym + " " + formatted : formatted + " " + sym;
    }

    openAllocations() {
        this.action.doAction("nn_fund_management.action_fund_allocation");
    }
    openRequisitions() {
        this.action.doAction("nn_fund_management.action_fund_requisition");
    }
    openTransfers() {
        this.action.doAction("nn_fund_management.action_fund_transfer");
    }
    openPendingVerification() {
        this.action.doAction("nn_fund_management.action_fund_incoming_pending");
    }
}

registry.category("actions").add("fund_management.Dashboard", FundDashboard);
