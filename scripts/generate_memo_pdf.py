"""Generate publication-quality Business Memo PDF for Oytra COD RTO Strategy."""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)

def build_pdf(filename="docs/business-memo.pdf"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    header_title = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#065f46')
    )
    header_meta = ParagraphStyle(
        'HeaderMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#475569')
    )
    section_h1 = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=8,
        spaceAfter=4
    )
    body_text = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#334155'),
        spaceAfter=4
    )
    bullet_text = ParagraphStyle(
        'BulletCustom',
        parent=body_text,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )
    callout_text = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#065f46')
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1e293b')
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#0f172a')
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("STRATEGIC MEMO: COD RTO INTELLIGENCE & PROFIT OPTIMIZATION", header_title))
    story.append(Spacer(1, 3))
    story.append(Paragraph("<b>To:</b> Founder & Leadership Team, Oytra &nbsp;&nbsp;|&nbsp;&nbsp; <b>From:</b> Associate Software Engineer &nbsp;&nbsp;|&nbsp;&nbsp; <b>Date:</b> October 31, 2026", header_meta))
    story.append(Paragraph("<b>Subject:</b> Empirical Findings from 1,988 COD Orders, Operations vs. Marketing Alignment, and Decision Policy", header_meta))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#10b981'), spaceAfter=6, spaceBefore=2))

    # Executive Summary Box
    summary_data = [[
        Paragraph(
            "<b>The Core Trade-off:</b> Cash on Delivery accounts for ~55% of our 3,000 monthly orders but carries a <b>28.4% Return to Origin (RTO) rate</b>, costing <b>₹169.40 per failed delivery</b>. Operations wants to aggressively cancel risky orders, but Marketing spent <b>₹300+ in Meta ad CAC</b> to acquire each buyer. Blind cancellations destroy ₹702 in gross profit and wasted CAC per genuine customer. By replacing binary 'Ship vs. Cancel' with an intelligent 4-tier routing policy (Ship As-Is, WhatsApp Confirmation, ₹40 Prepaid Nudge, and Hold/Cancel), we preserve marketing acquisition while cutting operational bleed.",
            callout_text
        )
    ]]
    summary_table = Table(summary_data, colWidths=[540])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ecfdf5')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#a7f3d0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 6))

    # 1. Three Surprising Findings
    story.append(Paragraph("1. Three Surprising Findings from the Historical Data (with Concrete Numbers)", section_h1))
    story.append(Paragraph(
        "<b>• Finding 1 — The 2+ Return Cliff:</b> Past customer delivery behavior is the single strongest predictor of return risk. In our dataset, buyers with 0 prior RTOs have a 27.1% baseline return rate, and buyers with 1 prior RTO return 35.2% of the time. However, buyers with <b>2 or more prior RTOs return 76.5% of the time</b> (more than 3 out of 4 packages refused). Customers who have refused 2 packages are habitual returners; halting COD for this small group carries near-zero risk of alienating viable buyers.",
        bullet_text
    ))
    story.append(Paragraph(
        "<b>• Finding 2 — Incomplete vs. Hinglish Addresses (Detail Trumps Dialect):</b> Customers with sparse or placeholder addresses (under 15 characters, single-word locations, or notes like <i>'xyz'</i> or <i>'call me'</i>) have a staggering <b>61.7% RTO failure rate</b>. In contrast, orders with colloquial Hindi/Hinglish landmark instructions (e.g., <i>'Station chowk se left, Hanuman Mandir ke saamne'</i>) achieved a <b>72.4% successful delivery rate</b>. Couriers fail when doors/flats are unidentifiable, not when customers use local directions. This is where Gemini LLM creates high ROI: understanding local context without penalizing genuine vernacular buyers.",
        bullet_text
    ))
    story.append(Paragraph(
        "<b>• Finding 3 — The Pincode Sparsity Trap (The Operations Blindspot):</b> Deliveries were scattered across <b>1,067 distinct pincodes</b>. But only <b>30 pincodes (2.8%) had 5 or more orders</b>, while over 82% had only 1 or 2 total orders. If we followed Operations' suggestion to 'block COD in bad pincodes', an area with a single unlucky returned order would be labelled '100% RTO', permanently blacklisting over 800 serviceable zones. Pincode history is only reliable with statistical volume (5+ orders); otherwise, regional baselines must be applied.",
        bullet_text
    ))
    story.append(Spacer(1, 4))

    # 2. Recommended Decision Rules & Historical Replay
    story.append(Paragraph("2. Recommended Decision Rules & Policy Replay on Last Month's Orders", section_h1))
    story.append(Paragraph("We evaluated all 1,988 orders into 4 action tiers based on an explainable 0–100 composite risk score:", body_text))

    policy_data = [
        [Paragraph("Action Bucket", table_cell_bold), Paragraph("Score Band", table_cell_bold), Paragraph("Order Count (%)", table_cell_bold), Paragraph("Actual RTO Rate", table_cell_bold), Paragraph("Operational Workflow & Economics", table_cell_bold)],
        [Paragraph("<b>1. Ship As-Is</b>", table_cell), Paragraph("0 – 30", table_cell), Paragraph("1,726 (86.8%)", table_cell), Paragraph("23.5%", table_cell), Paragraph("Frictionless dispatch to Delhivery. Protects brand conversion for repeat safe buyers.", table_cell)],
        [Paragraph("<b>2. WhatsApp Confirm</b>", table_cell), Paragraph("31 – 50", table_cell), Paragraph("210 (10.6%)", table_cell), Paragraph("59.5%", table_cell), Paragraph("First-time buyers with incomplete address/sparse pincode. Pauses dispatch until intent verified.", table_cell)],
        [Paragraph("<b>3. Nudge to Prepaid</b>", table_cell), Paragraph("51 – 70", table_cell), Paragraph("49 (2.5%)", table_cell), Paragraph("63.3%", table_cell), Paragraph("High risk first-timers. Offers ₹40 discount to convert to online payment, eliminating COD door refusal.", table_cell)],
        [Paragraph("<b>4. Hold / Cancel</b>", table_cell), Paragraph("71 – 100", table_cell), Paragraph("3 (0.15%)", table_cell), Paragraph("100.0%", table_cell), Paragraph("Serial returners (2+ prior RTOs) or verified fake test names. 100% precision saves ₹169.40/order.", table_cell)]
    ]
    policy_table = Table(policy_data, colWidths=[95, 55, 75, 75, 240])
    policy_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(policy_table)
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Simulated Financial Impact:</b> Cancelling the 3 serial returners saved <b>₹508.20</b> with zero false cancellations. Nudging the 49 high-risk orders with ₹40 discount converts ~25-30% to prepaid, generating <b>+₹597 net risk savings</b>. Halting unconfirmed orders in the WhatsApp tier prevents ~25 avoidable returns, saving another <b>₹4,235</b>.", body_text))

    story.append(Spacer(1, 4))

    # 3. Balancing Operations vs. Marketing
    story.append(Paragraph("3. Balancing Operations vs. Marketing: The Exact ₹ Math", section_h1))
    story.append(Paragraph(
        "Operations wants zero returns; Marketing wants maximum GMV. We resolve this tension using unit economics rather than subjective debate:<br/>"
        "• <b>Cost of 1 RTO = ₹169.40</b> (Forward ₹65 + Reverse ₹65 + Packaging ₹25 + 8% damage on ₹180 product = ₹14.40).<br/>"
        "• <b>Gross Margin per Order = 62%</b> (₹402.38 gross margin on our ₹649 average cart).<br/>"
        "• <b>Customer Acquisition Cost (CAC) = ₹300.00</b> spent upfront on Meta Ads.<br/>"
        "If we cancel a genuine customer by mistake, we don't just forfeit ₹402 in profit—we also waste the ₹300 spent to acquire them. <b>A false cancellation costs Oytra ₹702.38, which is over 4× more expensive than absorbing an RTO!</b><br/>"
        "Therefore, our policy establishes two non-negotiable guardrails:<br/>"
        "<b>1. First-Order Protection:</b> Never cancel a first-time buyer. If their address is questionable or pincode risky, route them to WhatsApp Confirmation or Prepaid Nudge. If they confirm or pay, we retain the ₹300 CAC investment and fulfill safely.<br/>"
        "<b>2. Why ₹40 Prepaid Discount Math Works:</b> Expected return cost on COD is 28% × ₹169.40 = <b>₹47.43</b>. Expected return cost on Prepaid is 4% × ₹169.40 = <b>₹6.78</b>. Converting an order from COD to Prepaid saves Oytra <b>₹40.65 in gross logistics risk</b>. Offering a ₹40 discount captures nearly the entire expected risk reduction while eliminating door friction and securing immediate cash flow.",
        body_text
    ))

    story.append(Spacer(1, 4))

    # 4. What Could Go Wrong & Monitoring
    story.append(Paragraph("4. What Could Go Wrong in Production & How We Notice", section_h1))
    story.append(Paragraph(
        "• <b>WhatsApp Failure / Customer on DND:</b> Customers may not have active WhatsApp or fail to check messages within 24 hours. <i>Safeguard:</i> Fallback SMS with one-click web confirmation link after 4 hours of inactivity.<br/>"
        "• <b>LLM False Positives on Unique Indian Names:</b> A rare regional name might be misclassified as placeholder text. <i>Safeguard:</i> Automated first-order protection overrides cancellation, and operations reviews a dedicated daily queue of held orders.<br/>"
        "• <b>Courier Regional Hub Disruptions:</b> Floods or local hub strikes can artificially spike a pincode's return rate. <i>Safeguard:</i> Daily Pincode Drift Alert triggers if 3+ RTOs occur in 48 hours for any pincode, notifying logistics to re-route couriers.",
        body_text
    ))

    story.append(Spacer(1, 4))

    # 5. What We Would Build Next
    story.append(Paragraph("5. Roadmap: What We Would Build with 2 More Weeks", section_h1))
    story.append(Paragraph(
        "<b>1. Live Shopify Webhook Listener & Fulfillment Hold API:</b> Automatically intercept orders via <code>orders/create</code> webhook and apply shipping tags (<code>RTO-Approved</code>, <code>Hold-WhatsApp</code>) directly in Shopify.<br/>"
        "<b>2. Official Meta WhatsApp Cloud API:</b> Upgrade from our simulator to live WhatsApp Business API with interactive Quick Reply buttons (<i>'Confirm Order'</i> / <i>'Pay Online ₹40 OFF'</i>).<br/>"
        "<b>3. Dynamic Courier Routing:</b> Route high-risk pincodes to couriers with better regional performance (Delhivery performs 5.4% better in Tier 2/3 towns compared to regional providers).<br/>"
        "<b>4. Calibrated ML Classifier (XGBoost):</b> Train a gradient-boosted tree on 10,000+ orders to refine risk scoring beyond heuristic weights.",
        body_text
    ))

    doc.build(story)
    print(f"✅ Generated {filename}")

if __name__ == "__main__":
    build_pdf("docs/business-memo.pdf")
