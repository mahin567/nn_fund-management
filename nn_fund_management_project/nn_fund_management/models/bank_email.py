# -*- coding: utf-8 -*-
import re
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# ── Per-bank regex patterns ───────────────────────────────────────────────────
# Each entry: (bank_name, subject_pattern, amount_pattern, ref_pattern, sender_pattern)
BANK_PATTERNS = [
    {
        'bank': 'BRAC Bank',
        'subject_keywords': ['brac', 'bkash', 'credit alert'],
        'amount_re': r'(?:BDT|Tk\.?|TK)\s*([0-9,]+(?:\.[0-9]{1,2})?)',
        'ref_re': r'(?:Ref(?:erence)?[:\s#]+)([A-Z0-9\-]{6,30})',
        'sender_re': r'(?:Sender|From|Name)[:\s]+([^\n\r,]+)',
    },
    {
        'bank': 'Dutch-Bangla Bank',
        'subject_keywords': ['dbbl', 'dutch-bangla', 'dutch bangla', 'nexus pay'],
        'amount_re': r'(?:BDT|Tk\.?|TK)\s*([0-9,]+(?:\.[0-9]{1,2})?)',
        'ref_re': r'(?:Transaction\s*ID|TxnID|Ref)[:\s]+([A-Z0-9]{6,30})',
        'sender_re': r'(?:Sender|Payer|From)[:\s]+([^\n\r,]+)',
    },
    {
        'bank': 'Islami Bank',
        'subject_keywords': ['islami bank', 'ibbl', 'cellfin'],
        'amount_re': r'(?:BDT|Tk\.?|TK)\s*([0-9,]+(?:\.[0-9]{1,2})?)',
        'ref_re': r'(?:Ref(?:erence)?[:\s]+)([A-Z0-9\-]{6,30})',
        'sender_re': r'(?:Sender|Remitter)[:\s]+([^\n\r,]+)',
    },
    {
        'bank': 'Generic',
        'subject_keywords': [],  # fallback — always tried last
        'amount_re': r'(?:BDT|Tk\.?|TK|Amount)[:\s]*([0-9,]+(?:\.[0-9]{1,2})?)',
        'ref_re': r'(?:Ref(?:erence)?|TxID|TransactionID)[:\s#]+([A-Z0-9\-]{6,30})',
        'sender_re': r'(?:Sender|From|Name|Payer)[:\s]+([^\n\r,]+)',
    },
]


def _parse_amount(raw):
    """Convert '1,23,456.78' → 123456.78"""
    try:
        return float(raw.replace(',', ''))
    except (ValueError, AttributeError):
        return None


class FundBankEmailTemplate(models.Model):
    """Configurable per-bank email parsing template.

    Admins can add or customise regex patterns for new banks without
    modifying Python source code.
    """
    _name = 'fund.bank.email.template'
    _description = 'Bank Email Parsing Template'
    _order = 'sequence'

    name = fields.Char(string='Bank / Template Name', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    subject_keywords = fields.Char(
        string='Subject Keywords (comma-separated)',
        help='If any keyword is found (case-insensitive) in the email subject, '
             'this template is selected. Leave empty to use as fallback.')
    amount_regex = fields.Char(
        string='Amount Regex', required=True,
        default=r'(?:BDT|Tk\.?|TK|Amount)[:\s]*([0-9,]+(?:\.[0-9]{1,2})?)',
        help='Group 1 must capture the numeric amount string.')
    ref_regex = fields.Char(
        string='Reference Regex', required=True,
        default=r'(?:Ref(?:erence)?|TxID)[:\s#]+([A-Z0-9\-]{6,30})',
        help='Group 1 must capture the transaction reference.')
    sender_regex = fields.Char(
        string='Sender Regex',
        default=r'(?:Sender|From|Name)[:\s]+([^\n\r,]+)',
        help='Group 1 must capture the sender/payer name. Optional.')

    default_fund_account_id = fields.Many2one(
        'fund.account', string='Default Fund Account',
        help='Parsed emails from this bank will be pre-filled with this account.')

    description = fields.Text(string='Notes')

    def _matches_subject(self, subject):
        self.ensure_one()
        if not self.subject_keywords:
            return True  # fallback template
        subject_lower = (subject or '').lower()
        keywords = [k.strip().lower() for k in self.subject_keywords.split(',') if k.strip()]
        return any(kw in subject_lower for kw in keywords)

    def _parse_body(self, body):
        """Return dict with amount, transaction_reference, source (or None for each)."""
        self.ensure_one()
        result = {'amount': None, 'transaction_reference': None, 'source': None}

        m = re.search(self.amount_regex, body, re.IGNORECASE)
        if m:
            result['amount'] = _parse_amount(m.group(1))

        m = re.search(self.ref_regex, body, re.IGNORECASE)
        if m:
            result['transaction_reference'] = m.group(1).strip()

        if self.sender_regex:
            m = re.search(self.sender_regex, body, re.IGNORECASE)
            if m:
                result['source'] = m.group(1).strip()

        return result


class FundBankEmailLog(models.Model):
    """Raw log of every email processed by the integration.

    Keeps the original message body so admins can debug parsing failures
    without needing to access the mail server again.
    """
    _name = 'fund.bank.email.log'
    _description = 'Bank Email Processing Log'
    _order = 'create_date desc'

    name = fields.Char(string='Email Subject', required=True)
    from_email = fields.Char(string='From Address')
    received_date = fields.Datetime(string='Received', default=fields.Datetime.now)
    body_preview = fields.Text(string='Body Preview (first 2000 chars)')
    message_id = fields.Char(string='Message-ID')

    status = fields.Selection([
        ('parsed', 'Parsed — Incoming Fund Created'),
        ('duplicate', 'Duplicate — Already Exists'),
        ('parse_error', 'Parse Error — Could Not Extract Data'),
        ('ignored', 'Ignored — No Matching Template'),
    ], string='Status', required=True, default='ignored')

    template_used = fields.Char(string='Template Used')
    incoming_fund_id = fields.Many2one('fund.incoming', string='Created Incoming Fund')
    error_details = fields.Text(string='Error Details')


class MailThread(models.AbstractModel):
    """Extend mail.thread to intercept inbound emails for fund notification parsing."""
    _inherit = 'mail.thread'

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None,
                      custom_values=None):
        """Intercept emails addressed to fund-management alias and try to parse them."""
        routes = super().message_route(
            message, message_dict, model=model, thread_id=thread_id,
            custom_values=custom_values)

        # Only act on emails routed to the fund incoming alias
        if model == 'fund.incoming':
            self.env['fund.incoming']._process_bank_email(message_dict)

        return routes


class FundIncomingEmailMixin(models.Model):
    """Adds email-parsing capability to fund.incoming."""
    _inherit = 'fund.incoming'

    source_email_from = fields.Char(string='Email Sender', copy=False, readonly=True)
    source_email_date = fields.Datetime(string='Email Received Date', copy=False, readonly=True)

    @api.model
    def _process_bank_email(self, message_dict):
        """Parse an inbound email dict and create a draft fund.incoming record."""
        subject = message_dict.get('subject', '') or ''
        body = message_dict.get('body', '') or ''
        from_email = message_dict.get('email_from', '') or ''
        message_id = message_dict.get('message_id', '') or ''

        log_vals = {
            'name': subject or '(no subject)',
            'from_email': from_email,
            'message_id': message_id,
            'body_preview': body[:2000],
            'status': 'ignored',
        }

        # Duplicate guard on Message-ID
        if message_id:
            existing = self.search([('source_email_message_id', '=', message_id)], limit=1)
            if existing:
                log_vals.update({'status': 'duplicate', 'incoming_fund_id': existing.id})
                self.env['fund.bank.email.log'].create(log_vals)
                _logger.info('fund.incoming: duplicate email ignored, message_id=%s', message_id)
                return

        # Find matching template (ordered by sequence; fallback last)
        templates = self.env['fund.bank.email.template'].search(
            [('active', '=', True)], order='sequence')
        matched_template = None
        for tpl in templates:
            if tpl._matches_subject(subject):
                matched_template = tpl
                break

        if not matched_template:
            self.env['fund.bank.email.log'].create(log_vals)
            _logger.info('fund.incoming: no template matched subject="%s"', subject)
            return

        log_vals['template_used'] = matched_template.name
        parsed = matched_template._parse_body(body)

        if not parsed['amount'] or not parsed['transaction_reference']:
            log_vals.update({
                'status': 'parse_error',
                'error_details': 'Could not extract amount=%s or ref=%s from body.' % (
                    parsed['amount'], parsed['transaction_reference']),
            })
            self.env['fund.bank.email.log'].create(log_vals)
            _logger.warning(
                'fund.incoming: parse failed for subject="%s", template=%s',
                subject, matched_template.name)
            return

        # Check for duplicate transaction reference per account
        fund_account = matched_template.default_fund_account_id
        if fund_account:
            dup = self.search([
                ('fund_account_id', '=', fund_account.id),
                ('transaction_reference', '=', parsed['transaction_reference']),
            ], limit=1)
            if dup:
                log_vals.update({'status': 'duplicate', 'incoming_fund_id': dup.id})
                self.env['fund.bank.email.log'].create(log_vals)
                return

        # Create draft incoming fund record
        vals = {
            'date': fields.Date.today(),
            'amount': parsed['amount'],
            'transaction_reference': parsed['transaction_reference'],
            'source': parsed.get('source') or from_email,
            'description': 'Auto-created from bank email: %s' % subject,
            'state': 'pending_verification',
            'source_email_message_id': message_id,
            'source_email_from': from_email,
            'source_email_date': fields.Datetime.now(),
        }
        if fund_account:
            vals['fund_account_id'] = fund_account.id

        try:
            new_rec = self.create(vals)
            log_vals.update({'status': 'parsed', 'incoming_fund_id': new_rec.id})
            _logger.info(
                'fund.incoming: created %s from email (amount=%.2f, ref=%s)',
                new_rec.name, parsed['amount'], parsed['transaction_reference'])
        except Exception as exc:
            log_vals.update({'status': 'parse_error', 'error_details': str(exc)})
            _logger.exception('fund.incoming: failed to create record from email')

        self.env['fund.bank.email.log'].create(log_vals)
