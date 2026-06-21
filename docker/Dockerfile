# ─────────────────────────────────────────────
# nn_fund_management — Odoo 17 Docker image
# ─────────────────────────────────────────────
FROM odoo:17.0

USER root

# Install any extra system packages here if needed
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     some-package \
#  && rm -rf /var/lib/apt/lists/*

# Copy the custom module into the extra-addons directory
COPY nn_fund_management/ /mnt/extra-addons/nn_fund_management/

# Copy Odoo config
COPY docker/odoo.conf /etc/odoo/odoo.conf

# Make sure Odoo owns its data directory
RUN chown -R odoo:odoo /mnt/extra-addons /etc/odoo/odoo.conf

USER odoo

# Expose Odoo HTTP and longpolling ports
EXPOSE 8069 8072

CMD ["odoo", "--config=/etc/odoo/odoo.conf"]