"""
Generate realistic Florida real estate PDF documents for testing AI extraction.

This script creates documents that closely mirror actual Florida real estate forms:
- FAR/BAR AS-IS Residential Contract for Sale and Purchase
- CFPB Closing Disclosure (TRID compliant)
- EPA Lead-Based Paint Disclosure (42 U.S.C. 4852d)
- Florida Seller's Real Property Disclosure (F.S. 689.25)
- HOA/Condo Disclosure (F.S. 718.503, F.S. 720.401)
- Home Inspection Report (Florida Standards of Practice 61-30)
- Title Commitment Summary
- Loan Estimate (TRID compliant)

Run with: python scripts/generate_sample_docs.py
"""

import os
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# We'll use reportlab to generate PDFs
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, ListFlowable, ListItem, KeepTogether
    )
except ImportError:
    print("Installing reportlab...")
    import subprocess
    subprocess.check_call(["pip", "install", "reportlab"])
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, ListFlowable, ListItem, KeepTogether
    )

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "sample_documents"
OUTPUT_DIR.mkdir(exist_ok=True)


def get_styles():
    """Get custom document styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=12
    ))

    styles.add(ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=11,
        spaceBefore=12,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        'Paragraph',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    ))

    styles.add(ParagraphStyle(
        'Legal',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor('#333333')
    ))

    styles.add(ParagraphStyle(
        'FieldLabel',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        'FieldValue',
        parent=styles['Normal'],
        fontSize=9
    ))

    styles.add(ParagraphStyle(
        'Conspicuous',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        spaceBefore=12,
        spaceAfter=12
    ))

    return styles


# ============================================================================
# FAR/BAR AS-IS RESIDENTIAL CONTRACT
# ============================================================================

def create_farbar_asis_contract(filename: str, tx: dict):
    """
    Create a realistic FAR/BAR AS-IS Residential Contract for Sale and Purchase.
    Based on Florida Realtors / Florida Bar standard form (Rev. 7/24).
    """
    doc = SimpleDocTemplate(
        str(OUTPUT_DIR / filename),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = get_styles()
    story = []

    # Header
    story.append(Paragraph(
        '"AS IS" RESIDENTIAL CONTRACT FOR SALE AND PURCHASE',
        styles['DocTitle']
    ))
    story.append(Paragraph(
        'THIS FORM HAS BEEN APPROVED BY THE FLORIDA REALTORS AND THE FLORIDA BAR',
        styles['DocSubtitle']
    ))
    story.append(Paragraph(
        f'Contract Date (Effective Date): {tx["effective"].strftime("%B %d, %Y")}',
        styles['FieldLabel']
    ))
    story.append(Spacer(1, 0.1*inch))

    # 1. PARTIES AND PROPERTY
    story.append(Paragraph('1. PARTIES AND PROPERTY', styles['SectionHeader']))

    parties_text = f"""
    <b>SELLER:</b> {tx['seller']}<br/>
    <b>BUYER:</b> {tx['buyer']}<br/>
    <b>Property Address:</b> {tx['address']}<br/>
    <b>Legal Description:</b> {tx['legal_description']}<br/>
    <b>County:</b> {tx['county']}, Florida<br/>
    <b>Parcel ID:</b> {tx['parcel_id']}
    """
    story.append(Paragraph(parties_text, styles['Paragraph']))

    # 2. PURCHASE PRICE AND CLOSING
    story.append(Paragraph('2. PURCHASE PRICE AND CLOSING', styles['SectionHeader']))

    earnest_money = tx['price'] * Decimal('0.03')
    balance = tx['price'] - earnest_money

    price_data = [
        ['(a) Purchase Price:', f"${tx['price']:,.2f}"],
        ['(b) Initial Deposit (Earnest Money):', f"${earnest_money:,.2f}"],
        ['    Held in escrow by:', tx['escrow_agent']],
        ['(c) Additional Deposit due within ___ days:', '$0.00'],
        ['(d) Balance to Close:', f"${balance:,.2f}"],
        ['', ''],
        ['CLOSING DATE:', tx['closing'].strftime('%B %d, %Y')],
        ['CLOSING LOCATION:', tx['title_company']],
    ]

    t = Table(price_data, colWidths=[2.5*inch, 3*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('FONTNAME', (0, 6), (0, 7), 'Helvetica-Bold'),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.1*inch))

    # 3. TIME FOR ACCEPTANCE
    story.append(Paragraph('3. TIME FOR ACCEPTANCE OF OFFER; EFFECTIVE DATE', styles['SectionHeader']))
    story.append(Paragraph(
        f'If this offer is not executed by and delivered to all parties OR FACT OF EXECUTION communicated '
        f'in writing between the parties on or before {(tx["effective"] + timedelta(days=3)).strftime("%B %d, %Y")}, '
        f'this offer shall be deemed withdrawn and the Deposit shall be returned to Buyer.',
        styles['Paragraph']
    ))

    # 4. FINANCING
    story.append(Paragraph('4. FINANCING', styles['SectionHeader']))

    if tx.get('financing_type') == 'conventional':
        financing_text = f"""
        [X] (a) <b>CONVENTIONAL FINANCING:</b> This Contract is contingent upon Buyer obtaining a commitment
        for a conventional mortgage loan for a principal amount not to exceed ${tx['loan_amount']:,.2f},
        at an initial interest rate not to exceed {tx['interest_rate']}% per annum, amortized over a
        period of not less than {tx['loan_term']} years.<br/><br/>

        Loan Approval Period: Buyer shall apply for the loan within 5 days after Effective Date and use
        good faith and diligent effort to obtain approval of the loan. If Buyer fails to obtain loan
        approval within {tx['financing_contingency_days']} days after Effective Date, Buyer may cancel
        this Contract by delivering written notice to Seller, and Buyer shall be refunded the Deposit.
        """
    elif tx.get('financing_type') == 'cash':
        financing_text = """
        [X] (b) <b>CASH:</b> No financing contingency. Buyer shall pay the Balance to Close in cash or
        immediately available funds at Closing. If this box is checked, the loan approval contingency
        in Paragraph 4(a) does not apply.
        """
    else:
        financing_text = """
        [X] (c) <b>FHA/VA FINANCING:</b> This Contract is contingent upon Buyer obtaining FHA or VA
        financing. Buyer shall apply within 5 days after Effective Date.
        """

    story.append(Paragraph(financing_text, styles['Paragraph']))

    # 5. TITLE EVIDENCE AND INSURANCE
    story.append(Paragraph('5. TITLE EVIDENCE AND INSURANCE', styles['SectionHeader']))
    story.append(Paragraph(f"""
    (a) <b>Title Evidence:</b> At least 15 days prior to Closing, Seller shall deliver to Buyer or Buyer's
    attorney a title insurance commitment issued by {tx['title_company']} as the title insurer,
    agreeing to issue to Buyer, upon recording of the deed to Buyer, an owner's policy of title
    insurance in the amount of the Purchase Price, insuring Buyer's title to the Property,
    subject only to: (i) Comprehensive Land Use Plans, Zoning, and other restrictions imposed
    by governmental authority; (ii) restrictions and easements common to the subdivision;
    (iii) outstanding oil, gas and mineral rights of record without right of entry; and
    (iv) matters shown on the survey, if any.<br/><br/>

    (b) <b>Title Insurance Premium:</b> The premium for the owner's title insurance policy shall be paid
    by [X] Seller [ ] Buyer at Closing.<br/><br/>

    (c) <b>Survey:</b> [ ] Buyer [X] Seller shall, within the time period for delivering title evidence,
    deliver to Buyer a current survey of the Property.
    """, styles['Paragraph']))

    # 6. PROPERTY CONDITION - AS IS
    story.append(Paragraph('6. PROPERTY CONDITION; AS IS', styles['SectionHeader']))

    # CONSPICUOUS NOTICE - This is critical for AI extraction
    story.append(Paragraph(
        'BUYER ACKNOWLEDGES AND AGREES THAT BUYER IS PURCHASING THE PROPERTY IN ITS '
        '"AS IS" CONDITION AND THAT BUYER, EXCEPT AS OTHERWISE STATED IN THIS CONTRACT, '
        'IS NOT RELYING ON ANY REPRESENTATIONS OR WARRANTIES OF ANY KIND WHATSOEVER '
        'FROM SELLER, ANY BROKER, OR ANY OF THEIR AGENTS OR REPRESENTATIVES AS TO ANY '
        'MATTERS CONCERNING THE PROPERTY.',
        styles['Conspicuous']
    ))

    story.append(Paragraph(f"""
    (a) <b>Inspection Period:</b> Buyer shall have {tx['inspection_days']} days from Effective Date
    ("Inspection Period") within which to have the Property inspected and to determine, in Buyer's
    sole discretion, whether the Property is acceptable to Buyer. During the Inspection Period,
    Buyer may cancel this Contract by delivering written notice to Seller, and Buyer shall be
    refunded the Deposit.<br/><br/>

    (b) <b>Seller Disclosure:</b> Seller shall, within 3 days after Effective Date, deliver to Buyer
    the following disclosures and documents, as applicable:<br/>
    • Seller's Real Property Disclosure Statement (F.S. 689.25)<br/>
    • Lead-Based Paint Disclosure (42 U.S.C. 4852d) if Property was built before 1978<br/>
    • Homeowners' Association/Condominium Disclosure (F.S. 720.401, F.S. 718.503)<br/>
    • Coastal Construction Control Line (CCCL) Information<br/>
    • Property Tax Disclosure Summary (F.S. 689.261)
    """, styles['Paragraph']))

    # 7. CLOSING COSTS, FEES AND CHARGES
    story.append(Paragraph('7. CLOSING COSTS, FEES AND CHARGES', styles['SectionHeader']))

    story.append(Paragraph(f"""
    (a) <b>Seller's Closing Services:</b> Seller shall pay for Seller's attorney's fees, abstract continuation
    or title search, Seller's portion of closing service fee (as defined in F.S. 627.7711), documentary
    stamps on deed, and prorations as of Closing Date.<br/><br/>

    (b) <b>Buyer's Closing Services:</b> Buyer shall pay for Buyer's attorney's fees, recording fees for the
    deed and financing documents, Buyer's portion of closing service fee, intangible tax on new mortgage,
    and prorations as of Closing Date.<br/><br/>

    (c) <b>Special Assessments:</b> Certified, confirmed and ratified special assessment liens as of Closing
    Date shall be paid by Seller. Pending liens as of Closing shall be assumed by Buyer.<br/><br/>

    Estimated Closing Costs for Buyer: ${tx['estimated_buyer_closing_costs']:,.2f}<br/>
    Estimated Closing Costs for Seller: ${tx['estimated_seller_closing_costs']:,.2f}
    """, styles['Paragraph']))

    # 8. PRORATIONS
    story.append(Paragraph('8. PRORATIONS', styles['SectionHeader']))
    story.append(Paragraph(f"""
    Real property taxes, interest, rents, association fees, and other expenses of the Property shall be
    prorated as of the day before Closing. Cash at Closing shall be increased or decreased as may be
    required by prorations.<br/><br/>

    <b>Property Tax Proration Method:</b> [X] Based on {tx['tax_year']} taxes [ ] Based on current year's taxes<br/>
    <b>Prior Year Property Taxes:</b> ${tx['annual_property_tax']:,.2f}<br/>
    <b>HOA/Condo Assessment Proration:</b> ${tx['hoa_fee']:,.2f}/month
    """, styles['Paragraph']))

    # 9. RISK OF LOSS
    story.append(Paragraph('9. RISK OF LOSS', styles['SectionHeader']))
    story.append(Paragraph("""
    Risk of loss to the Property by fire or other casualty prior to Closing is on Seller. If the Property
    is damaged by fire or other casualty before Closing and the cost of restoration does not exceed 1.5%
    of the Purchase Price, Seller shall restore the Property to its pre-casualty condition. If the cost
    exceeds 1.5%, Buyer may: (a) take the Property "as is" together with either the 1.5% or any insurance
    proceeds payable as a result of the casualty; or (b) cancel the Contract and receive the Deposit.
    """, styles['Paragraph']))

    # 10. ASSIGNABILITY
    story.append(Paragraph('10. ASSIGNABILITY', styles['SectionHeader']))
    story.append(Paragraph("""
    [X] This Contract is assignable. Buyer may assign this Contract and Buyer's rights under it to any
    person or entity, provided such assignment is in writing and a copy is delivered to Seller within
    5 days after the assignment. The original Buyer shall remain liable under this Contract unless
    Seller agrees in writing to release the original Buyer.
    """, styles['Paragraph']))

    # Page break
    story.append(PageBreak())

    # 11. DEFAULT
    story.append(Paragraph('11. DEFAULT', styles['SectionHeader']))
    story.append(Paragraph("""
    (a) <b>BUYER DEFAULT:</b> If Buyer fails to perform any obligation under this Contract within the time
    specified, including timely payment of all deposits, Seller may elect to: (i) seek specific performance;
    or (ii) cancel this Contract and receive the Deposit as liquidated damages, thereby releasing Buyer
    and Seller from all further obligations under this Contract. If Seller elects to receive the Deposit
    as liquidated damages, Seller authorizes Escrow Agent to release the Deposit to Seller without further
    notice to Buyer, subject to Chapter 475, F.S.<br/><br/>

    (b) <b>SELLER DEFAULT:</b> If Seller fails to perform any obligation under this Contract within the time
    specified, Buyer may elect to: (i) seek specific performance; (ii) seek damages; or (iii) cancel this
    Contract and receive the Deposit and be reimbursed for reasonable expenses incurred in examining title
    and inspecting the Property.
    """, styles['Paragraph']))

    # 12. DISPUTE RESOLUTION
    story.append(Paragraph('12. DISPUTE RESOLUTION; ATTORNEY\'S FEES', styles['SectionHeader']))
    story.append(Paragraph("""
    (a) <b>MEDIATION:</b> Before filing any lawsuit or arbitration relating to this Contract, the parties
    shall attempt to resolve any dispute through mediation pursuant to Florida Rules for Certified and
    Court-Appointed Mediators. Mediation is a prerequisite to filing a lawsuit or arbitration.<br/><br/>

    (b) <b>ATTORNEY'S FEES:</b> In any litigation or arbitration arising from this Contract, the prevailing
    party shall be entitled to recover reasonable attorney's fees and costs.
    """, styles['Paragraph']))

    # 13. ESCROW
    story.append(Paragraph('13. ESCROW', styles['SectionHeader']))
    story.append(Paragraph(f"""
    <b>Escrow Agent:</b> {tx['escrow_agent']}<br/>
    <b>Escrow Agent Address:</b> {tx['escrow_agent_address']}<br/>
    <b>Escrow Agent Phone:</b> {tx['escrow_agent_phone']}<br/><br/>

    Escrow Agent agrees to hold the Deposit in trust pending the outcome of this transaction. Escrow Agent
    is authorized to disburse the Deposit in accordance with the terms of this Contract and applicable
    Florida law (Chapter 475, F.S.).
    """, styles['Paragraph']))

    # 14. ADDITIONAL TERMS
    story.append(Paragraph('14. ADDITIONAL TERMS AND CONDITIONS', styles['SectionHeader']))

    additional_terms = tx.get('additional_terms', [
        'Seller to provide a home warranty at closing, cost not to exceed $500.',
        'Seller to leave all window treatments and ceiling fans.',
        'Personal property included: Refrigerator, washer, dryer.'
    ])

    terms_text = '<br/>'.join([f'• {term}' for term in additional_terms])
    story.append(Paragraph(terms_text, styles['Paragraph']))

    # SIGNATURES
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph('SIGNATURES', styles['SectionHeader']))

    story.append(Paragraph("""
    THIS IS A LEGALLY BINDING CONTRACT. IF NOT FULLY UNDERSTOOD, SEEK THE ADVICE OF AN ATTORNEY
    PRIOR TO SIGNING. THIS FORM HAS BEEN APPROVED BY THE FLORIDA REALTORS AND THE FLORIDA BAR.
    """, styles['Conspicuous']))

    story.append(Spacer(1, 0.2*inch))

    # Signature lines
    sig_data = [
        ['BUYER SIGNATURE:', '________________________', 'Date:', tx['effective'].strftime('%m/%d/%Y')],
        ['Print Name:', tx['buyer'], '', ''],
        ['', '', '', ''],
        ['SELLER SIGNATURE:', '________________________', 'Date:', tx['effective'].strftime('%m/%d/%Y')],
        ['Print Name:', tx['seller'], '', ''],
    ]

    t = Table(sig_data, colWidths=[1.5*inch, 2.5*inch, 0.5*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 3), (0, 3), 'Helvetica-Bold'),
    ]))
    story.append(t)

    # Broker information
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph('BROKER INFORMATION', styles['SectionHeader']))

    broker_data = [
        ['Listing Broker:', tx.get('listing_broker', 'Sunshine Realty Group')],
        ['Listing Agent:', tx.get('listing_agent', 'Maria Rodriguez')],
        ['License #:', tx.get('listing_agent_license', 'SL3456789')],
        ['', ''],
        ['Selling Broker:', tx.get('selling_broker', 'Coastal Properties LLC')],
        ['Selling Agent:', tx.get('selling_agent', 'James Thompson')],
        ['License #:', tx.get('selling_agent_license', 'BK1234567')],
    ]

    t = Table(broker_data, colWidths=[1.5*inch, 3.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    story.append(t)

    # Footer
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        f'FAR/BAR AS-IS-6xx Rev. 7/24 | Page 2 of 2',
        ParagraphStyle('Footer', fontSize=8, alignment=TA_CENTER, textColor=colors.gray)
    ))

    doc.build(story)
    print(f"Created: {filename}")


# ============================================================================
# CFPB CLOSING DISCLOSURE (TRID)
# ============================================================================

def create_closing_disclosure(filename: str, tx: dict):
    """
    Create a realistic CFPB Closing Disclosure form.
    Based on the TILA-RESPA Integrated Disclosure (TRID) requirements.
    """
    doc = SimpleDocTemplate(
        str(OUTPUT_DIR / filename),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = get_styles()
    story = []

    # Calculate loan amounts
    loan_amount = tx.get('loan_amount', tx['price'] * Decimal('0.80'))
    down_payment = tx['price'] - loan_amount
    interest_rate = tx.get('interest_rate', Decimal('6.875'))
    monthly_pi = loan_amount * (interest_rate / Decimal('100') / Decimal('12')) / (
        1 - (1 + interest_rate / Decimal('100') / Decimal('12')) ** -360
    )
    monthly_escrow = tx.get('annual_property_tax', Decimal('8500')) / Decimal('12') + Decimal('185')  # tax + insurance
    monthly_total = monthly_pi + monthly_escrow

    # Header
    story.append(Paragraph('Closing Disclosure', styles['DocTitle']))
    story.append(Paragraph(
        'This form is a statement of final loan terms and closing costs. Compare this '
        'document with your Loan Estimate.',
        styles['DocSubtitle']
    ))

    story.append(Spacer(1, 0.1*inch))

    # Top info table
    top_info = [
        ['Closing Information', '', 'Transaction Information', ''],
        ['Date Issued', tx['closing'].strftime('%m/%d/%Y'), 'Borrower', tx['buyer']],
        ['Closing Date', tx['closing'].strftime('%m/%d/%Y'), '', tx.get('buyer_address', '123 Current St, Miami, FL')],
        ['Disbursement Date', tx['closing'].strftime('%m/%d/%Y'), 'Seller', tx['seller']],
        ['Settlement Agent', tx['title_company'].split()[0], '', tx['address']],
        ['File #', f'TC-{random.randint(100000, 999999)}', 'Lender', tx.get('lender', 'First National Bank')],
        ['Property', tx['address'], '', ''],
    ]

    t = Table(top_info, colWidths=[1.2*inch, 2*inch, 1.2*inch, 2.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8E8E8')),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.15*inch))

    # LOAN TERMS section
    story.append(Paragraph('Loan Terms', styles['SectionHeader']))

    loan_terms = [
        ['Loan Amount', f'${loan_amount:,.2f}', 'Can this amount increase after closing?', 'NO'],
        ['Interest Rate', f'{interest_rate}%', 'Can this amount increase after closing?', 'NO'],
        ['Monthly Principal & Interest', f'${monthly_pi:,.2f}', 'Can this amount increase after closing?', 'NO'],
    ]

    t = Table(loan_terms, colWidths=[1.5*inch, 1.5*inch, 2.5*inch, 1*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.gray),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.1*inch))

    # Prepayment Penalty / Balloon Payment
    pp_data = [
        ['Prepayment Penalty', 'NO', 'As high as $ N/A if you pay off the loan during the first N/A years'],
        ['Balloon Payment', 'NO', 'You do not have a balloon payment with this loan'],
    ]
    t = Table(pp_data, colWidths=[1.5*inch, 0.5*inch, 4.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.15*inch))

    # PROJECTED PAYMENTS
    story.append(Paragraph('Projected Payments', styles['SectionHeader']))

    payment_data = [
        ['Payment Calculation', 'Years 1-30'],
        ['Principal & Interest', f'${monthly_pi:,.2f}'],
        ['Mortgage Insurance', '$0.00' if down_payment >= tx['price'] * Decimal('0.20') else '$85.00'],
        ['Estimated Escrow', f'${monthly_escrow:,.2f}'],
        ['', ''],
        ['Estimated Total Monthly Payment', f'${monthly_total:,.2f}'],
    ]

    t = Table(payment_data, colWidths=[2.5*inch, 2*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 5), (0, 5), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8E8E8')),
        ('LINEABOVE', (0, 5), (-1, 5), 1, colors.black),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph("""
    <b>Escrow Account:</b> Your lender will establish an escrow account for property taxes and
    homeowner's insurance. You will pay $892.00 at closing for initial escrow and approximately
    $892.00/month thereafter.
    """, styles['Legal']))

    # COSTS AT CLOSING
    story.append(Paragraph('Costs at Closing', styles['SectionHeader']))

    origination_fee = loan_amount * Decimal('0.01')
    appraisal_fee = Decimal('550')
    credit_report = Decimal('45')
    title_insurance = tx['price'] * Decimal('0.005')
    recording_fees = Decimal('175')
    transfer_taxes = tx['price'] * Decimal('0.007')  # FL doc stamps

    total_closing_costs = origination_fee + appraisal_fee + credit_report + title_insurance + recording_fees + transfer_taxes
    total_cash_to_close = down_payment + total_closing_costs

    costs_data = [
        ['Closing Costs', f'${total_closing_costs:,.2f}', 'Includes all fees and costs itemized in Section J-K'],
        ['Cash to Close', f'${total_cash_to_close:,.2f}', 'Includes closing costs, see Calculating Cash to Close'],
    ]

    t = Table(costs_data, colWidths=[1.5*inch, 1.5*inch, 3.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    story.append(t)

    # Page 2 - Closing Cost Details
    story.append(PageBreak())
    story.append(Paragraph('Closing Cost Details', styles['DocTitle']))

    # J. LOAN COSTS
    story.append(Paragraph('J. Loan Costs', styles['SectionHeader']))

    loan_costs = [
        ['A. Origination Charges', '', f'${origination_fee:,.2f}'],
        ['  01 Loan Origination Fee (1.00%)', f'${origination_fee:,.2f}', ''],
        ['B. Services You Cannot Shop For', '', f'${appraisal_fee + credit_report:,.2f}'],
        ['  01 Appraisal Fee', f'${appraisal_fee:,.2f}', ''],
        ['  02 Credit Report', f'${credit_report:,.2f}', ''],
        ['C. Services You Did Shop For', '', '$0.00'],
        ['', '', ''],
        ['J. TOTAL LOAN COSTS', '', f'${origination_fee + appraisal_fee + credit_report:,.2f}'],
    ]

    t = Table(loan_costs, colWidths=[3.5*inch, 1.2*inch, 1.2*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 2), (0, 2), 'Helvetica-Bold'),
        ('FONTNAME', (0, 5), (0, 5), 'Helvetica-Bold'),
        ('FONTNAME', (0, 7), (-1, 7), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, 7), (-1, 7), 1, colors.black),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.1*inch))

    # K. OTHER COSTS
    story.append(Paragraph('K. Other Costs', styles['SectionHeader']))

    other_costs = [
        ['E. Taxes and Government Fees', '', f'${recording_fees + transfer_taxes:,.2f}'],
        ['  01 Recording Fees', f'${recording_fees:,.2f}', ''],
        ['  02 Transfer Taxes (Documentary Stamps)', f'${transfer_taxes:,.2f}', ''],
        ['F. Prepaids', '', f'${tx["annual_property_tax"] / Decimal("12") * 2:,.2f}'],
        ['  01 Homeowner\'s Insurance Premium (12 mo.)', '$2,220.00', ''],
        ['  02 Prepaid Interest', '$450.00', ''],
        ['G. Initial Escrow Payment at Closing', '', '$892.00'],
        ['  01 Homeowner\'s Insurance (2 mo.)', '$370.00', ''],
        ['  02 Property Taxes (2 mo.)', '$522.00', ''],
        ['H. Other', '', f'${title_insurance:,.2f}'],
        ['  01 Owner\'s Title Insurance', f'${title_insurance:,.2f}', ''],
        ['', '', ''],
        ['K. TOTAL OTHER COSTS', '', f'${recording_fees + transfer_taxes + title_insurance + Decimal("892"):,.2f}'],
    ]

    t = Table(other_costs, colWidths=[3.5*inch, 1.2*inch, 1.2*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 3), (0, 3), 'Helvetica-Bold'),
        ('FONTNAME', (0, 6), (0, 6), 'Helvetica-Bold'),
        ('FONTNAME', (0, 9), (0, 9), 'Helvetica-Bold'),
        ('FONTNAME', (0, 12), (-1, 12), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, 12), (-1, 12), 1, colors.black),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
    ]))
    story.append(t)

    # L. TOTAL CLOSING COSTS
    story.append(Spacer(1, 0.1*inch))
    total_line = [
        ['L. TOTAL CLOSING COSTS (J + K)', '', f'${total_closing_costs:,.2f}'],
    ]
    t = Table(total_line, colWidths=[3.5*inch, 1.2*inch, 1.2*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8E8E8')),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
    ]))
    story.append(t)

    # Calculating Cash to Close
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph('Calculating Cash to Close', styles['SectionHeader']))

    earnest_deposit = tx['price'] * Decimal('0.03')
    seller_credits = tx.get('seller_credits', Decimal('0'))

    cash_calc = [
        ['Total Closing Costs (J + K)', f'${total_closing_costs:,.2f}'],
        ['Less: Closing Costs Financed', '$0.00'],
        ['Less: Down Payment/Funds from Borrower', f'${down_payment:,.2f}'],
        ['Less: Deposit', f'-${earnest_deposit:,.2f}'],
        ['Less: Funds for Borrower', '$0.00'],
        ['Less: Seller Credits', f'-${seller_credits:,.2f}'],
        ['', ''],
        ['CASH TO CLOSE', f'${total_cash_to_close - earnest_deposit - seller_credits:,.2f}'],
    ]

    t = Table(cash_calc, colWidths=[3.5*inch, 2*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 7), (-1, 7), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, 7), (-1, 7), 1, colors.black),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    story.append(t)

    # Contact Information
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph('Contact Information', styles['SectionHeader']))

    contact_data = [
        ['Lender', tx.get('lender', 'First National Bank'), 'Settlement Agent', tx['title_company']],
        ['NMLS ID', f'{random.randint(100000, 999999)}', 'File #', f'TC-{random.randint(100000, 999999)}'],
        ['Address', tx.get('lender_address', '100 Bank Plaza, Miami, FL 33131'),
         'Address', tx.get('title_company_address', '200 Title Way, Miami, FL 33131')],
        ['Phone', '(305) 555-1234', 'Phone', '(305) 555-5678'],
    ]

    t = Table(contact_data, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    story.append(t)

    # Confirm Receipt
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph('Confirm Receipt', styles['SectionHeader']))
    story.append(Paragraph("""
    By signing, you are only confirming that you have received this form. You do not have to
    accept this loan because you have signed or received this form.
    """, styles['Legal']))

    story.append(Spacer(1, 0.2*inch))
    sig_data = [
        ['Applicant Signature:', '________________________', 'Date:', '___________'],
        ['Co-Applicant Signature:', '________________________', 'Date:', '___________'],
    ]
    t = Table(sig_data, colWidths=[1.5*inch, 2.5*inch, 0.5*inch, 1.5*inch])
    story.append(t)

    doc.build(story)
    print(f"Created: {filename}")


# ============================================================================
# EPA LEAD-BASED PAINT DISCLOSURE
# ============================================================================

def create_lead_paint_disclosure(filename: str, tx: dict):
    """
    Create an EPA Lead-Based Paint Disclosure form.
    Required by 42 U.S.C. 4852d for homes built before 1978.
    """
    doc = SimpleDocTemplate(
        str(OUTPUT_DIR / filename),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = get_styles()
    story = []

    # Header
    story.append(Paragraph(
        'DISCLOSURE OF INFORMATION ON LEAD-BASED PAINT AND/OR LEAD-BASED PAINT HAZARDS',
        styles['DocTitle']
    ))
    story.append(Paragraph(
        'Lead Warning Statement',
        styles['SectionHeader']
    ))

    story.append(Paragraph("""
    <b>Housing built before 1978 may contain lead-based paint. Lead from paint, paint chips, and
    dust can pose health hazards if not managed properly. Lead exposure is especially harmful to
    young children and pregnant women.</b> Before renting pre-1978 housing, lessors must disclose
    the presence of known lead-based paint and/or lead-based paint hazards in the dwelling.
    Buyers/Lessees must also receive a federally approved pamphlet on lead poisoning prevention.
    """, styles['Paragraph']))

    story.append(Spacer(1, 0.1*inch))

    # Property Information
    story.append(Paragraph('Property Information', styles['SectionHeader']))
    property_info = [
        ['Property Address:', tx['address']],
        ['Year Built:', str(tx['year_built'])],
        ['Seller(s):', tx['seller']],
        ['Buyer(s):', tx['buyer']],
    ]
    t = Table(property_info, colWidths=[1.5*inch, 4.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.15*inch))

    # Seller's Disclosure
    story.append(Paragraph("SELLER'S DISCLOSURE (initial)", styles['SectionHeader']))

    has_lead = tx.get('has_known_lead', False)
    has_records = tx.get('has_lead_records', False)

    if has_lead:
        disclosure_text = """
        (a) Presence of lead-based paint and/or lead-based paint hazards (check (i) or (ii) below):<br/><br/>

        [ ] (i) Known lead-based paint and/or lead-based paint hazards are present in the housing
        (explain): ___________________________________________________________________________<br/><br/>

        [X] (ii) Seller has no knowledge of lead-based paint and/or lead-based paint hazards in
        the housing.
        """
    else:
        disclosure_text = """
        (a) Presence of lead-based paint and/or lead-based paint hazards (check (i) or (ii) below):<br/><br/>

        [ ] (i) Known lead-based paint and/or lead-based paint hazards are present in the housing
        (explain): ___________________________________________________________________________<br/><br/>

        [X] (ii) Seller has no knowledge of lead-based paint and/or lead-based paint hazards in
        the housing.
        """

    story.append(Paragraph(disclosure_text, styles['Paragraph']))

    if has_records:
        records_text = """
        (b) Records and reports available to the seller (check (i) or (ii) below):<br/><br/>

        [X] (i) Seller has provided the buyer with all available records and reports pertaining
        to lead-based paint and/or lead-based paint hazards in the housing (list documents):
        Lead inspection report dated _________________<br/><br/>

        [ ] (ii) Seller has no reports or records pertaining to lead-based paint and/or lead-based
        paint hazards in the housing.
        """
    else:
        records_text = """
        (b) Records and reports available to the seller (check (i) or (ii) below):<br/><br/>

        [ ] (i) Seller has provided the buyer with all available records and reports pertaining
        to lead-based paint and/or lead-based paint hazards in the housing (list documents):
        __________________________________________________________________________________<br/><br/>

        [X] (ii) Seller has no reports or records pertaining to lead-based paint and/or lead-based
        paint hazards in the housing.
        """

    story.append(Paragraph(records_text, styles['Paragraph']))
    story.append(Spacer(1, 0.1*inch))

    # Buyer's Acknowledgment
    story.append(Paragraph("BUYER'S ACKNOWLEDGMENT (initial)", styles['SectionHeader']))

    story.append(Paragraph("""
    (c) Buyer has received copies of all information listed above.<br/><br/>

    (d) Buyer has received the pamphlet <i>Protect Your Family From Lead in Your Home</i>.<br/><br/>

    (e) Buyer has (check (i) or (ii) below):<br/><br/>

    [X] (i) Received a 10-day opportunity (or mutually agreed upon period) to conduct a risk
    assessment or inspection for the presence of lead-based paint and/or lead-based paint hazards; or<br/><br/>

    [ ] (ii) Waived the opportunity to conduct a risk assessment or inspection for the presence of
    lead-based paint and/or lead-based paint hazards.
    """, styles['Paragraph']))
    story.append(Spacer(1, 0.1*inch))

    # Agent's Acknowledgment
    story.append(Paragraph("AGENT'S ACKNOWLEDGMENT (initial)", styles['SectionHeader']))
    story.append(Paragraph("""
    (f) Agent has informed the seller of the seller's obligations under 42 U.S.C. 4852d and is
    aware of his/her responsibility to ensure compliance.
    """, styles['Paragraph']))
    story.append(Spacer(1, 0.15*inch))

    # Certification of Accuracy
    story.append(Paragraph('CERTIFICATION OF ACCURACY', styles['SectionHeader']))
    story.append(Paragraph("""
    The following parties have reviewed the information above and certify, to the best of their
    knowledge, that the information they have provided is true and accurate.
    """, styles['Paragraph']))

    story.append(Spacer(1, 0.2*inch))

    # Signature block
    sig_data = [
        ['', 'Signature', 'Date'],
        ['Seller:', '________________________________', '_______________'],
        ['Seller:', '________________________________', '_______________'],
        ['', '', ''],
        ['Buyer:', '________________________________', '_______________'],
        ['Buyer:', '________________________________', '_______________'],
        ['', '', ''],
        ['Agent:', '________________________________', '_______________'],
        ['Agent:', '________________________________', '_______________'],
    ]

    t = Table(sig_data, colWidths=[1*inch, 3.5*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'),
    ]))
    story.append(t)

    # Legal notice
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("""
    <b>PENALTIES:</b> Violators can be subject to civil and criminal sanctions including fines
    up to $46,517 per violation for civil penalties and up to $100,000 and/or imprisonment for
    up to one year for criminal penalties. (24 CFR Part 35.86 and 40 CFR Part 745.118)
    """, styles['Legal']))

    doc.build(story)
    print(f"Created: {filename}")


# ============================================================================
# FLORIDA SELLER'S PROPERTY DISCLOSURE
# ============================================================================

def create_sellers_disclosure(filename: str, tx: dict):
    """
    Create a Florida Seller's Real Property Disclosure Statement.
    Per F.S. 689.25 requirements.
    """
    doc = SimpleDocTemplate(
        str(OUTPUT_DIR / filename),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = get_styles()
    story = []

    # Header
    story.append(Paragraph(
        "SELLER'S REAL PROPERTY DISCLOSURE STATEMENT",
        styles['DocTitle']
    ))
    story.append(Paragraph(
        'Pursuant to Florida Statute 689.25',
        styles['DocSubtitle']
    ))

    # Legal notice
    story.append(Paragraph("""
    In Florida, a seller of residential property is obligated to disclose to a buyer all facts
    known to a seller that materially and adversely affect the value of the property being sold
    and which are not readily observable by a buyer. This disclosure statement is designed to
    assist the seller in complying with disclosure requirements under Florida law.
    """, styles['Legal']))
    story.append(Spacer(1, 0.1*inch))

    # Property Information
    story.append(Paragraph('PROPERTY INFORMATION', styles['SectionHeader']))

    prop_info = [
        ['Property Address:', tx['address']],
        ['Legal Description:', tx['legal_description']],
        ['County:', f"{tx['county']}, Florida"],
        ['Parcel ID:', tx['parcel_id']],
        ['Year Built:', str(tx['year_built'])],
        ['Square Footage:', f"{tx.get('square_feet', 2450):,} sq ft"],
        ['Bedrooms/Bathrooms:', f"{tx.get('bedrooms', 4)} BR / {tx.get('bathrooms', '2.5')} BA"],
    ]

    t = Table(prop_info, colWidths=[1.5*inch, 4.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.15*inch))

    # Occupancy
    story.append(Paragraph('OCCUPANCY', styles['SectionHeader']))
    story.append(Paragraph(f"""
    1. Has the property been occupied by the current owner? [X] Yes [ ] No<br/>
    2. If yes, how long has the current owner occupied the property? {tx.get('occupancy_years', 8)} years<br/>
    3. Is the property currently vacant? [ ] Yes [X] No<br/>
    4. Is the property currently rented? [ ] Yes [X] No
    """, styles['Paragraph']))

    # Structural
    story.append(Paragraph('STRUCTURAL', styles['SectionHeader']))

    structural_issues = tx.get('structural_issues', False)
    foundation_type = tx.get('foundation_type', 'Concrete Block')
    roof_age = tx.get('roof_age', 12)

    story.append(Paragraph(f"""
    5. Foundation Type: [{"X" if foundation_type == "Concrete Block" else " "}] Concrete Block
       [{"X" if foundation_type == "Slab" else " "}] Slab [{"X" if foundation_type == "Crawl Space" else " "}] Crawl Space
       [{"X" if foundation_type == "Other" else " "}] Other<br/>
    6. Are you aware of any settling, shifting, or structural problems? [{"X" if structural_issues else " "}] Yes [{" " if structural_issues else "X"}] No<br/>
    7. Approximate age of roof: {roof_age} years<br/>
    8. Are you aware of any roof leaks (past or present)? [ ] Yes [X] No<br/>
    9. Has the roof been repaired or replaced? [X] Yes [ ] No  If yes, when? 2019<br/>
    10. Are you aware of any water intrusion or moisture problems? [ ] Yes [X] No
    """, styles['Paragraph']))

    # Plumbing
    story.append(Paragraph('PLUMBING', styles['SectionHeader']))
    story.append(Paragraph(f"""
    11. Type of water supply: [X] Public Water [ ] Private Well [ ] Community Well<br/>
    12. Type of sewage system: [X] Public Sewer [ ] Septic Tank [ ] Other<br/>
    13. If septic, date of last inspection: N/A<br/>
    14. Type of water heater: [X] Electric [ ] Gas [ ] Tankless  Age: {tx.get('water_heater_age', 6)} years<br/>
    15. Type of pipes: [X] Copper [ ] PVC [ ] Galvanized [ ] Polybutylene [ ] Unknown<br/>
    16. Are you aware of any plumbing problems or leaks? [ ] Yes [X] No<br/>
    17. Has the property ever experienced sewage backup? [ ] Yes [X] No
    """, styles['Paragraph']))

    # Electrical
    story.append(Paragraph('ELECTRICAL', styles['SectionHeader']))
    story.append(Paragraph(f"""
    18. Electrical service: [ ] 100 AMP [X] 200 AMP [ ] Other<br/>
    19. Are you aware of any electrical problems? [ ] Yes [X] No<br/>
    20. Has the property ever had aluminum wiring? [ ] Yes [X] No [ ] Unknown<br/>
    21. Are there GFCI outlets in kitchen and bathrooms? [X] Yes [ ] No [ ] Unknown
    """, styles['Paragraph']))

    # HVAC
    story.append(Paragraph('HEATING AND AIR CONDITIONING', styles['SectionHeader']))
    story.append(Paragraph(f"""
    22. Type of heating: [X] Central Electric [ ] Central Gas [ ] Heat Pump [ ] Other<br/>
    23. Type of air conditioning: [X] Central [ ] Window Units [ ] None<br/>
    24. Age of HVAC system: {tx.get('hvac_age', 8)} years<br/>
    25. Date of last service: {tx.get('hvac_last_service', 'March 2025')}<br/>
    26. Are you aware of any problems with the heating or cooling systems? [ ] Yes [X] No
    """, styles['Paragraph']))

    # Page break for more sections
    story.append(PageBreak())

    # Environmental
    story.append(Paragraph('ENVIRONMENTAL', styles['SectionHeader']))

    flood_zone = tx.get('flood_zone', False)
    sinkhole = tx.get('sinkhole_activity', False)

    story.append(Paragraph(f"""
    27. Is the property in a designated flood zone? [{"X" if flood_zone else " "}] Yes [{" " if flood_zone else "X"}] No<br/>
    28. Has the property ever experienced flooding? [ ] Yes [X] No<br/>
    29. Is flood insurance required? [{"X" if flood_zone else " "}] Yes [{" " if flood_zone else "X"}] No<br/>
    30. Are you aware of any sinkholes on or near the property? [{"X" if sinkhole else " "}] Yes [{" " if sinkhole else "X"}] No<br/>
    31. Are you aware of any soil or drainage problems? [ ] Yes [X] No<br/>
    32. Are you aware of any environmental hazards (asbestos, radon, mold, Chinese drywall, etc.)? [ ] Yes [X] No<br/>
    33. Has the property ever been tested for radon? [ ] Yes [X] No<br/>
    34. Are there any underground storage tanks on the property? [ ] Yes [X] No
    """, styles['Paragraph']))

    # Termites/Pests
    story.append(Paragraph('TERMITES AND PESTS', styles['SectionHeader']))
    story.append(Paragraph(f"""
    35. Are you aware of any past or present termite or wood-destroying organism damage? [ ] Yes [X] No<br/>
    36. Is there an active termite bond/warranty? [X] Yes [ ] No<br/>
        If yes, company name: Orkin Pest Control<br/>
        Bond expires: December 2026<br/>
    37. Date of last WDO inspection: {tx.get('wdo_inspection_date', 'January 2025')}<br/>
    38. Were any repairs made as a result of termite damage? [ ] Yes [X] No
    """, styles['Paragraph']))

    # Pool/Spa
    has_pool = tx.get('has_pool', True)
    if has_pool:
        story.append(Paragraph('POOL AND SPA', styles['SectionHeader']))
        story.append(Paragraph("""
        39. Type of pool: [X] In-ground [ ] Above-ground [ ] None<br/>
        40. Pool surface: [X] Plaster [ ] Pebble [ ] Fiberglass [ ] Vinyl<br/>
        41. Is there a pool heater? [X] Yes [ ] No  Type: [X] Electric [ ] Gas [ ] Solar<br/>
        42. Is there a spa/hot tub? [ ] Yes [X] No<br/>
        43. Are you aware of any pool/spa problems? [ ] Yes [X] No<br/>
        44. Does the pool have required safety features per F.S. 515.27? [X] Yes [ ] No<br/>
            (Door alarms, pool fence, screen enclosure, or self-closing/self-latching doors)
        """, styles['Paragraph']))

    # HOA/Community
    has_hoa = tx.get('hoa_fee', 0) > 0
    if has_hoa:
        story.append(Paragraph('HOMEOWNERS ASSOCIATION/COMMUNITY', styles['SectionHeader']))
        story.append(Paragraph(f"""
        45. Is the property subject to a Homeowners Association? [X] Yes [ ] No<br/>
        46. HOA Name: {tx.get('hoa', 'N/A')}<br/>
        47. Current monthly/quarterly assessment: ${tx.get('hoa_fee', 0):,.2f}/month<br/>
        48. Are there any pending special assessments? [ ] Yes [X] No<br/>
        49. Are you aware of any HOA violations? [ ] Yes [X] No<br/>
        50. Is there a master association? [ ] Yes [X] No
        """, styles['Paragraph']))

    # Additional Disclosures
    story.append(Paragraph('ADDITIONAL DISCLOSURES', styles['SectionHeader']))
    story.append(Paragraph("""
    51. Are you aware of any easements, encroachments, or boundary disputes? [ ] Yes [X] No<br/>
    52. Are you aware of any pending litigation affecting the property? [ ] Yes [X] No<br/>
    53. Are you aware of any code violations (current or past)? [ ] Yes [X] No<br/>
    54. Has any work been done without required permits? [ ] Yes [X] No<br/>
    55. Are there any leased items (solar panels, water softener, alarm, etc.)? [ ] Yes [X] No<br/>
    56. Are you aware of any deaths on the property? [ ] Yes [X] No<br/>
    57. Are there any other material defects not disclosed above? [ ] Yes [X] No
    """, styles['Paragraph']))

    # Seller Certification
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph('SELLER CERTIFICATION', styles['SectionHeader']))
    story.append(Paragraph("""
    The undersigned Seller certifies that the information provided herein is true and accurate
    to the best of Seller's knowledge as of the date signed below. Seller agrees to notify
    Buyer of any changes in the above information prior to closing. This disclosure is not
    intended to be a warranty of any kind by the Seller.
    """, styles['Paragraph']))

    story.append(Spacer(1, 0.2*inch))

    sig_data = [
        ['Seller Signature:', '________________________', 'Date:', tx['effective'].strftime('%m/%d/%Y')],
        ['Print Name:', tx['seller'], '', ''],
        ['', '', '', ''],
        ['Seller Signature:', '________________________', 'Date:', tx['effective'].strftime('%m/%d/%Y')],
        ['Print Name:', '', '', ''],
    ]

    t = Table(sig_data, colWidths=[1.5*inch, 2.5*inch, 0.5*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t)

    # Buyer Receipt
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph('BUYER RECEIPT', styles['SectionHeader']))
    story.append(Paragraph("""
    Buyer acknowledges receipt of this Seller's Real Property Disclosure Statement and
    understands that this information is not a substitute for any inspections or warranties
    the buyer may wish to obtain.
    """, styles['Paragraph']))

    buyer_sig = [
        ['Buyer Signature:', '________________________', 'Date:', '_______________'],
        ['Print Name:', tx['buyer'], '', ''],
    ]

    t = Table(buyer_sig, colWidths=[1.5*inch, 2.5*inch, 0.5*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t)

    doc.build(story)
    print(f"Created: {filename}")


# ============================================================================
# HOA/CONDO DISCLOSURE
# ============================================================================

def create_hoa_disclosure(filename: str, tx: dict):
    """
    Create an HOA/Condo Disclosure document.
    Per F.S. 720.401 (HOA) and F.S. 718.503 (Condo).
    """
    doc = SimpleDocTemplate(
        str(OUTPUT_DIR / filename),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = get_styles()
    story = []

    is_condo = tx.get('is_condo', 'Condo' in tx['address'] or 'Unit' in tx['address'])

    if is_condo:
        # Condo disclosure per F.S. 718.503
        story.append(Paragraph(
            'CONDOMINIUM DISCLOSURE SUMMARY',
            styles['DocTitle']
        ))
        story.append(Paragraph(
            'Pursuant to Florida Statute 718.503',
            styles['DocSubtitle']
        ))

        story.append(Paragraph(
            'BUYER SHOULD NOT EXECUTE THIS CONTRACT UNTIL BUYER HAS RECEIVED AND READ '
            'THE CONDOMINIUM DOCUMENTS. IF THE REQUIRED DOCUMENTS ARE NOT PROVIDED TO '
            'THE BUYER PRIOR TO CLOSING, THE BUYER MAY VOID THE CONTRACT BY DELIVERING '
            'WRITTEN NOTICE TO THE SELLER WITHIN 3 DAYS AFTER RECEIVING ALL OF THE DOCUMENTS.',
            styles['Conspicuous']
        ))
    else:
        # HOA disclosure per F.S. 720.401
        story.append(Paragraph(
            'HOMEOWNERS\' ASSOCIATION DISCLOSURE SUMMARY',
            styles['DocTitle']
        ))
        story.append(Paragraph(
            'Pursuant to Florida Statute 720.401',
            styles['DocSubtitle']
        ))

        story.append(Paragraph(
            'IF THE DISCLOSURE SUMMARY REQUIRED BY SECTION 720.401, FLORIDA STATUTES, '
            'HAS NOT BEEN PROVIDED TO THE PROSPECTIVE BUYER BEFORE EXECUTING THIS CONTRACT '
            'FOR SALE, THIS CONTRACT IS VOIDABLE BY BUYER BY DELIVERING TO SELLER OR SELLER\'S '
            'AGENT WRITTEN NOTICE OF THE BUYER\'S INTENTION TO CANCEL WITHIN 3 DAYS AFTER '
            'RECEIPT OF THE DISCLOSURE SUMMARY OR PRIOR TO CLOSING, WHICHEVER OCCURS FIRST.',
            styles['Conspicuous']
        ))

    story.append(Spacer(1, 0.15*inch))

    # Property and Association Information
    story.append(Paragraph('PROPERTY AND ASSOCIATION INFORMATION', styles['SectionHeader']))

    info_data = [
        ['Property Address:', tx['address']],
        ['Association Name:', tx.get('hoa', 'Community Association')],
        ['Management Company:', tx.get('hoa_management', 'FirstService Residential')],
        ['Management Phone:', tx.get('hoa_phone', '(305) 555-4567')],
        ['Management Email:', tx.get('hoa_email', 'info@fsresidential.com')],
    ]

    t = Table(info_data, colWidths=[1.8*inch, 4.2*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.15*inch))

    # Assessment Information
    story.append(Paragraph('ASSESSMENT INFORMATION', styles['SectionHeader']))

    monthly_fee = tx.get('hoa_fee', Decimal('350'))
    special_assessment = tx.get('special_assessment', Decimal('0'))
    initiation_fee = tx.get('hoa_initiation_fee', Decimal('250'))

    assessment_data = [
        ['Current Regular Assessment:', f'${monthly_fee:,.2f} per month'],
        ['Assessment Due Date:', 'First of each month'],
        ['Special Assessments (Current/Pending):', f'${special_assessment:,.2f}' if special_assessment > 0 else 'None currently pending'],
        ['Capital Contribution/Initiation Fee:', f'${initiation_fee:,.2f}'],
        ['Application/Transfer Fee:', f'${tx.get("hoa_transfer_fee", Decimal("100")):,.2f}'],
        ['Move-In/Move-Out Fee:', f'${tx.get("hoa_move_fee", Decimal("200")):,.2f}'],
    ]

    t = Table(assessment_data, colWidths=[2.5*inch, 3.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.1*inch))

    if is_condo:
        # Additional condo-specific info per new 2024 requirements
        story.append(Paragraph('STRUCTURAL INTEGRITY AND RESERVES (New 2024 Requirements)', styles['SectionHeader']))

        story.append(Paragraph(f"""
        <b>Milestone Inspection:</b><br/>
        [ ] The building has not yet reached the milestone inspection age (25/30 years).<br/>
        [X] A milestone inspection has been completed. Date: {tx.get('milestone_inspection_date', 'October 2024')}<br/>
        [ ] A milestone inspection is required but has not been completed.<br/><br/>

        <b>Structural Integrity Reserve Study (SIRS):</b><br/>
        [X] A SIRS has been completed. Date: {tx.get('sirs_date', 'November 2024')}<br/>
        [ ] A SIRS has not been completed.<br/><br/>

        <b>Reserve Funding:</b><br/>
        Current Reserve Balance: ${tx.get('reserve_balance', 1850000):,.2f}<br/>
        Minimum Required Reserves: ${tx.get('required_reserves', 1500000):,.2f}<br/>
        Reserve Funding Status: [X] Fully Funded [ ] Partially Funded [ ] Underfunded<br/>
        """, styles['Paragraph']))

    # Association Rights and Restrictions
    story.append(Paragraph('ASSOCIATION RIGHTS AND RESTRICTIONS', styles['SectionHeader']))

    story.append(Paragraph(f"""
    <b>Buyer Approval Required:</b> [X] Yes [ ] No<br/>
    Approval Timeframe: Within 30 days of application submission<br/><br/>

    <b>Rental Restrictions:</b><br/>
    [{"X" if tx.get('rental_allowed', True) else " "}] Rentals are permitted<br/>
    [{"X" if tx.get('rental_restrictions', True) else " "}] Rental restrictions apply (minimum lease term: {tx.get('min_lease_term', 12)} months)<br/>
    [ ] Rentals are prohibited<br/>
    Maximum rentals per year: {tx.get('max_rentals_per_year', 2)}<br/><br/>

    <b>Pet Restrictions:</b><br/>
    [X] Pets are allowed with restrictions<br/>
    Maximum weight: {tx.get('pet_max_weight', 50)} lbs<br/>
    Maximum number of pets: {tx.get('max_pets', 2)}<br/>
    Breed restrictions: {tx.get('breed_restrictions', 'No aggressive breeds')}<br/><br/>

    <b>Other Restrictions:</b><br/>
    • Vehicle parking: {tx.get('parking_restrictions', 'Maximum 2 vehicles per unit')}<br/>
    • Guest parking: {tx.get('guest_parking', 'Available in designated areas')}<br/>
    • Satellite dishes: {tx.get('satellite_policy', 'Permitted on balcony/patio only')}<br/>
    • Exterior modifications: {tx.get('exterior_modifications', 'Require ARB approval')}<br/>
    """, styles['Paragraph']))

    # Insurance Information
    story.append(Paragraph('INSURANCE INFORMATION', styles['SectionHeader']))
    story.append(Paragraph(f"""
    <b>Master Policy Coverage:</b><br/>
    Property/Building: ${tx.get('master_property_coverage', 50000000):,.0f}<br/>
    Liability: ${tx.get('master_liability_coverage', 5000000):,.0f}<br/>
    Flood Insurance: [{"X" if tx.get('has_flood_insurance', True) else " "}] Yes [ ] No<br/>
    Fidelity Bond: [X] Yes [ ] No<br/><br/>

    <b>Unit Owner Requirements:</b><br/>
    HO-6 Policy Required: [X] Yes [ ] No<br/>
    Minimum Coverage: ${tx.get('min_ho6_coverage', 100000):,.0f}<br/>
    """, styles['Paragraph']))

    # Documents Provided
    story.append(Paragraph('DOCUMENTS PROVIDED TO BUYER', styles['SectionHeader']))
    story.append(Paragraph("""
    The following documents have been provided to Buyer:<br/>
    [X] Declaration of Covenants, Conditions, and Restrictions (CC&Rs)<br/>
    [X] Articles of Incorporation<br/>
    [X] Bylaws<br/>
    [X] Rules and Regulations<br/>
    [X] Current Year Budget<br/>
    [X] Most Recent Financial Statements<br/>
    [X] FAQ/Frequently Asked Questions Sheet<br/>
    [X] Estoppel Letter (to be provided at closing)<br/>
    """, styles['Paragraph']))

    # Acknowledgments
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph('BUYER ACKNOWLEDGMENT', styles['SectionHeader']))
    story.append(Paragraph("""
    Buyer acknowledges receipt of this disclosure summary and copies of the governing documents
    listed above. Buyer understands that membership in the association is mandatory and that
    failure to pay assessments may result in a lien against the property.
    """, styles['Paragraph']))

    story.append(Spacer(1, 0.2*inch))

    sig_data = [
        ['Buyer Signature:', '________________________', 'Date:', '_______________'],
        ['Print Name:', tx['buyer'], '', ''],
        ['', '', '', ''],
        ['Seller Signature:', '________________________', 'Date:', '_______________'],
        ['Print Name:', tx['seller'], '', ''],
    ]

    t = Table(sig_data, colWidths=[1.5*inch, 2.5*inch, 0.5*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t)

    doc.build(story)
    print(f"Created: {filename}")


# ============================================================================
# HOME INSPECTION REPORT
# ============================================================================

def create_inspection_report(filename: str, tx: dict):
    """
    Create a detailed home inspection report.
    Based on Florida Standards of Practice 61-30.
    """
    doc = SimpleDocTemplate(
        str(OUTPUT_DIR / filename),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = get_styles()
    story = []

    # Header
    story.append(Paragraph('HOME INSPECTION REPORT', styles['DocTitle']))
    story.append(Paragraph(
        'Prepared in Accordance with Florida Administrative Code 61-30',
        styles['DocSubtitle']
    ))

    inspector_name = tx.get('inspector_name', 'Michael J. Thompson, HI-7892')
    inspection_date = tx.get('inspection_date', tx['effective'] + timedelta(days=5))

    # Report Information
    info_data = [
        ['Property Address:', tx['address']],
        ['Inspection Date:', inspection_date.strftime('%B %d, %Y')],
        ['Inspector:', inspector_name],
        ['License Number:', 'HI-7892'],
        ['Company:', 'Florida Home Inspections, LLC'],
        ['Client:', tx['buyer']],
        ['Report Number:', f'FHI-{random.randint(10000, 99999)}'],
    ]

    t = Table(info_data, colWidths=[1.5*inch, 4.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F5F5')),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.15*inch))

    # Property Description
    story.append(Paragraph('PROPERTY DESCRIPTION', styles['SectionHeader']))
    story.append(Paragraph(f"""
    <b>Year Built:</b> {tx['year_built']}<br/>
    <b>Type:</b> {'Condominium' if 'Unit' in tx['address'] else 'Single Family Residence'}<br/>
    <b>Stories:</b> {tx.get('stories', 2)}<br/>
    <b>Square Footage:</b> {tx.get('square_feet', 2450):,} sq ft (per county records)<br/>
    <b>Foundation:</b> {tx.get('foundation_type', 'Concrete Block')}<br/>
    <b>Present at Inspection:</b> Buyer's Agent - {tx.get('listing_agent', 'Maria Rodriguez')}<br/>
    <b>Weather Conditions:</b> {tx.get('weather', 'Clear, 82°F')}<br/>
    <b>Utilities:</b> All utilities were on at time of inspection
    """, styles['Paragraph']))

    # Inspection Summary Legend
    story.append(Paragraph('CONDITION RATING LEGEND', styles['SectionHeader']))

    legend_data = [
        ['[S] Satisfactory', 'Component is functioning as intended with no deficiencies noted'],
        ['[M] Marginal', 'Component is functioning but showing signs of wear or minor issues'],
        ['[D] Deficient', 'Component requires repair, replacement, or further evaluation'],
        ['[NI] Not Inspected', 'Component was inaccessible or not present'],
        ['[NP] Not Present', 'Component does not exist in this property'],
    ]

    t = Table(legend_data, colWidths=[1.2*inch, 4.8*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.1*inch))

    # Generate inspection items based on property characteristics
    roof_age = tx.get('roof_age', 12)
    hvac_age = tx.get('hvac_age', 8)
    has_pool = tx.get('has_pool', True)

    # Determine some random but realistic issues
    issues = tx.get('inspection_issues', [])
    if not issues:
        possible_issues = [
            'Minor grout deterioration in master bathroom tile',
            'Kitchen faucet shows slight drip - recommend repair',
            'Missing weather stripping on garage entry door',
            'One GFCI outlet in garage not functional',
            'Minor wood rot at exterior door frame - recommend repair',
            'Attic insulation below current code (R-19 vs R-30 required)',
            'Condensate drain line shows algae buildup',
            'Pool screen has small tear in section C',
        ]
        # Pick 2-4 issues randomly
        num_issues = random.randint(2, 4)
        issues = random.sample(possible_issues, num_issues)

    # Inspection sections
    sections = [
        ('ROOF', 'S' if roof_age < 10 else 'M', [
            f'Roof Type: {tx.get("roof_type", "Asphalt Shingle")}',
            f'Approximate Age: {roof_age} years',
            f'Condition: {"Good condition with normal wear" if roof_age < 15 else "Showing age-appropriate wear"}',
            'Flashing: Properly installed at all penetrations',
            'Gutters and Downspouts: Functional, properly draining',
            'Visible Leaks: None observed',
        ]),
        ('EXTERIOR', 'S', [
            f'Siding Type: {tx.get("siding_type", "Stucco")}',
            'Condition: Good, no significant cracks or damage',
            'Windows: Dual pane, operational, seals intact',
            'Doors: Functional, hardware in good condition',
            'Walkways/Driveway: Minor settling cracks (typical)',
            'Landscaping Drainage: Slopes away from foundation',
        ]),
        ('FOUNDATION', 'S', [
            f'Foundation Type: {tx.get("foundation_type", "Concrete Block")}',
            'Visible Cracks: None observed',
            'Settlement: No evidence of unusual settlement',
            'Water Intrusion: No signs of moisture penetration',
            'Clearance: Adequate clearance from soil to siding',
        ]),
        ('ELECTRICAL', 'M' if any('electrical' in i.lower() or 'gfci' in i.lower() for i in issues) else 'S', [
            'Service Panel: 200 AMP, Square D brand',
            'Panel Location: Garage (accessible)',
            'Wiring Type: Copper (modern)',
            'GFCI Protection: Present in kitchen, bathrooms, garage, exterior',
            'AFCI Protection: Present in bedrooms (per code)',
            'Smoke/CO Detectors: Present and functional',
        ]),
        ('PLUMBING', 'M' if any('faucet' in i.lower() or 'plumbing' in i.lower() for i in issues) else 'S', [
            'Supply Lines: Copper',
            'Drain Lines: PVC',
            f'Water Heater: Electric, {tx.get("water_heater_age", 6)} years old',
            'Water Pressure: 55 PSI (within normal range 40-80 PSI)',
            'Fixtures: Functional with adequate flow',
            'Visible Leaks: None observed at time of inspection',
        ]),
        ('HVAC', 'S' if hvac_age < 10 else 'M', [
            f'System Type: Split system heat pump',
            f'Brand/Model: Carrier / 24ACC636A003',
            f'Approximate Age: {hvac_age} years (typical lifespan 15-20 years)',
            f'Cooling: Operational, 18°F differential (target 15-20°F)',
            f'Heating: Operational',
            f'Air Handler: Located in garage, clean, no visible issues',
            f'Ductwork: Insulated flex duct, no visible damage',
            f'Thermostat: Programmable, functional',
        ]),
        ('INTERIOR', 'M' if any('grout' in i.lower() or 'door' in i.lower() for i in issues) else 'S', [
            'Walls: Drywall, good condition, minor nail pops (typical)',
            'Ceilings: No stains or damage observed',
            'Floors: Tile (main areas), carpet (bedrooms) - good condition',
            'Doors: All operational with functional hardware',
            'Windows: Operational, seals intact',
            'Stairs/Railings: Secure, proper height',
        ]),
        ('ATTIC', 'M' if any('insulation' in i.lower() or 'attic' in i.lower() for i in issues) else 'S', [
            f'Access: Garage ceiling hatch',
            f'Insulation Type: Blown fiberglass',
            f'Insulation Level: R-19 (current code requires R-30)',
            f'Ventilation: Ridge vents and soffit vents present',
            f'Visible Moisture: None observed',
            f'Visible Pests: None observed',
        ]),
        ('KITCHEN', 'S', [
            'Cabinets: Wood, good condition',
            'Countertops: Granite, good condition',
            'Sink: Stainless steel, undermount',
            'Disposal: Functional',
            'Dishwasher: Functional, no visible leaks',
            'Range/Oven: Gas, functional',
            'Range Hood: Vented to exterior, functional',
            'Microwave: Built-in, functional',
        ]),
        ('BATHROOMS', 'M' if any('grout' in i.lower() or 'bathroom' in i.lower() for i in issues) else 'S', [
            'Master Bath: Dual vanity, walk-in shower, garden tub',
            'Guest Bath: Single vanity, tub/shower combo',
            'Half Bath: Powder room, functional',
            'Ventilation: Exhaust fans present and functional',
            'Caulking/Grout: Generally good, minor maintenance recommended',
            'Plumbing: All fixtures operational',
        ]),
        ('GARAGE', 'S', [
            f'Type: Attached, {tx.get("garage_spaces", 2)}-car',
            'Vehicle Door: Automatic, functional, safety reverse operational',
            'Floor: Concrete, minor cracks (typical)',
            'Fire Separation: Drywall, properly installed',
            'GFCI Outlets: Present and functional',
        ]),
    ]

    if has_pool:
        sections.append(('POOL/SPA', 'M' if any('pool' in i.lower() for i in issues) else 'S', [
            f'Pool Type: In-ground, {tx.get("pool_surface", "Pebble Tec")} finish',
            f'Approximate Size: {tx.get("pool_size", "15x30")} feet',
            'Pump and Motor: Operational',
            'Filter: Cartridge type, clean',
            'Heater: Electric, functional',
            'Deck: Pavers, good condition',
            'Screen Enclosure: Aluminum frame, generally good condition',
            'Safety Features: Door alarm and self-closing gate present',
        ]))

    # Print inspection sections
    for section_name, rating, items in sections:
        story.append(Paragraph(f'{section_name} [{rating}]', styles['SectionHeader']))
        items_text = '<br/>'.join([f'• {item}' for item in items])
        story.append(Paragraph(items_text, styles['Paragraph']))
        story.append(Spacer(1, 0.05*inch))

    # Page break for summary
    story.append(PageBreak())

    # Summary of Concerns
    story.append(Paragraph('SUMMARY OF CONCERNS', styles['SectionHeader']))
    story.append(Paragraph("""
    The following items require attention, repair, or further evaluation by a qualified
    professional. Items are listed in order of priority:
    """, styles['Paragraph']))

    story.append(Spacer(1, 0.1*inch))

    # Priority items
    priority_num = 1
    for issue in issues:
        story.append(Paragraph(f'<b>{priority_num}. {issue}</b>', styles['Paragraph']))
        priority_num += 1

    story.append(Spacer(1, 0.15*inch))

    # Maintenance Recommendations
    story.append(Paragraph('MAINTENANCE RECOMMENDATIONS', styles['SectionHeader']))
    story.append(Paragraph("""
    The following are general maintenance recommendations for this property:<br/><br/>
    • Service HVAC system annually<br/>
    • Clean gutters and downspouts semi-annually<br/>
    • Test smoke and CO detectors monthly, replace batteries annually<br/>
    • Inspect and clean dryer vent annually<br/>
    • Check water heater anode rod every 3-5 years<br/>
    • Maintain proper drainage away from foundation<br/>
    • Inspect caulking around windows, doors, and plumbing fixtures annually<br/>
    • Have septic system inspected every 3 years (if applicable)<br/>
    • Maintain pool water chemistry and equipment per manufacturer recommendations
    """, styles['Paragraph']))

    # Limitations
    story.append(Paragraph('LIMITATIONS AND EXCLUSIONS', styles['SectionHeader']))
    story.append(Paragraph("""
    This inspection is a visual, non-invasive examination of the accessible areas of the
    property as defined by Florida Administrative Code 61-30. This inspection does not include:<br/><br/>
    • Areas concealed or inaccessible<br/>
    • Cosmetic defects<br/>
    • Environmental hazards (mold, asbestos, lead, radon)<br/>
    • Code compliance verification<br/>
    • Pest/termite inspection (separate WDO report recommended)<br/>
    • Pool/spa equipment detailed analysis<br/>
    • Low voltage systems (security, audio, smart home)<br/>
    • Solar panel systems<br/>
    • Underground utilities or septic systems<br/><br/>

    This report represents the condition of the property at the time of inspection. Conditions
    may change over time. This report is not a warranty or guarantee.
    """, styles['Paragraph']))

    # Inspector Certification
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph('INSPECTOR CERTIFICATION', styles['SectionHeader']))
    story.append(Paragraph(f"""
    I certify that I have personally inspected the above-referenced property and that this
    report represents my professional opinion of its condition based on my observations at
    the time of inspection.
    """, styles['Paragraph']))

    story.append(Spacer(1, 0.2*inch))

    sig_data = [
        ['Inspector Signature:', '________________________', 'Date:', inspection_date.strftime('%m/%d/%Y')],
        ['Print Name:', inspector_name, '', ''],
        ['License #:', 'HI-7892', 'Expires:', '12/31/2026'],
    ]

    t = Table(sig_data, colWidths=[1.5*inch, 2.5*inch, 0.8*inch, 1.2*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    # Footer
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(
        'Florida Home Inspections, LLC | 1234 Inspector Lane, Miami, FL 33139 | (305) 555-INSP | www.flhomeinspect.com',
        ParagraphStyle('Footer', fontSize=8, alignment=TA_CENTER, textColor=colors.gray)
    ))

    doc.build(story)
    print(f"Created: {filename}")


# ============================================================================
# TITLE COMMITMENT
# ============================================================================

def create_title_commitment(filename: str, tx: dict):
    """
    Create a Title Commitment Summary document.
    Standard Florida title insurance commitment format.
    """
    doc = SimpleDocTemplate(
        str(OUTPUT_DIR / filename),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = get_styles()
    story = []

    commitment_date = tx['effective'] + timedelta(days=7)
    commitment_number = f"TC-{random.randint(100000, 999999)}"

    # Header
    story.append(Paragraph('COMMITMENT FOR TITLE INSURANCE', styles['DocTitle']))
    story.append(Paragraph(tx['title_company'], styles['DocSubtitle']))
    story.append(Spacer(1, 0.15*inch))

    # Commitment Info
    info_data = [
        ['Commitment Number:', commitment_number],
        ['Effective Date:', commitment_date.strftime('%B %d, %Y at 8:00 AM')],
        ['Policy Amount:', f"${tx['price']:,.2f}"],
        ['Premium:', f"${tx['price'] * Decimal('0.00575'):,.2f}"],
    ]

    t = Table(info_data, colWidths=[1.8*inch, 4.2*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.15*inch))

    # Property Description
    story.append(Paragraph('SCHEDULE A', styles['SectionHeader']))
    story.append(Paragraph(f"""
    <b>1. Policy or Policies to be issued:</b><br/>
    (a) ALTA Owner's Policy (Form 2021): Amount ${tx['price']:,.2f}<br/>
        Proposed Insured: {tx['buyer']}<br/><br/>

    (b) ALTA Loan Policy (Form 2021): Amount ${tx.get('loan_amount', tx['price'] * Decimal('0.80')):,.2f}<br/>
        Proposed Insured: {tx.get('lender', 'First National Bank')} and/or assigns<br/><br/>

    <b>2. The estate or interest in the land described in this Commitment is:</b><br/>
    Fee Simple<br/><br/>

    <b>3. Title to the estate or interest in the land is at the Effective Date vested in:</b><br/>
    {tx['seller']}<br/><br/>

    <b>4. The land referred to in this Commitment is described as follows:</b><br/>
    {tx['legal_description']}<br/><br/>

    Property Address: {tx['address']}<br/>
    Parcel ID: {tx['parcel_id']}
    """, styles['Paragraph']))

    # Schedule B-I Requirements
    story.append(Paragraph('SCHEDULE B-I (REQUIREMENTS)', styles['SectionHeader']))
    story.append(Paragraph("""
    The following requirements must be met prior to closing:<br/><br/>

    1. Payment of the full consideration to, or for the account of, the grantors or mortgagors.<br/><br/>

    2. Instruments sufficient to create the estate or interest to be insured must be properly
       executed, delivered and recorded.<br/><br/>

    3. Satisfactory evidence that all taxes, levies and assessments on said land which are
       due and payable have been paid.<br/><br/>

    4. Pay off statement from current mortgagee(s) of record confirming that upon receipt of
       the payoff amount, the lien will be released and mortgage satisfaction recorded.<br/><br/>

    5. Estoppel letter from the homeowners/condominium association confirming assessment status
       and any outstanding violations.<br/><br/>

    6. Survey certified to the proposed insured(s) and the title company, dated within 90 days
       of closing.<br/><br/>

    7. Proof of identity of all parties to the transaction (government-issued photo ID).
    """, styles['Paragraph']))

    # Schedule B-II Exceptions
    story.append(Paragraph('SCHEDULE B-II (EXCEPTIONS)', styles['SectionHeader']))
    story.append(Paragraph("""
    The Policy or Policies to be issued will contain exceptions to the following matters
    unless the same are disposed of to the satisfaction of the Company:<br/><br/>

    <b>STANDARD EXCEPTIONS:</b><br/>
    1. Taxes for the year of closing and subsequent years, which are not yet due and payable.<br/><br/>

    2. Covenants, conditions, restrictions, reservations, easements, and other matters of record,
       if any, including but not limited to those set forth in the recorded declaration of
       covenants and restrictions for the subdivision/condominium.<br/><br/>

    3. Any facts, rights, interests, or claims that are not shown by the public records but
       that could be ascertained by an inspection of the land or by making inquiry of persons
       in possession of the land.<br/><br/>

    4. Easements, liens, or encumbrances, or claims thereof, not shown by the public records.<br/><br/>

    5. Any encroachment, encumbrance, violation, variation, or adverse circumstance affecting
       the title that would be disclosed by an accurate and complete land survey of the land.<br/><br/>

    6. Any lien, or right to a lien, for services, labor, or material heretofore or hereafter
       furnished, imposed by law and not shown by the public records.<br/><br/>

    <b>SPECIAL EXCEPTIONS:</b><br/>
    """, styles['Paragraph']))

    # Add specific exceptions based on property
    exceptions = [
        f"7. Declaration of Covenants and Restrictions recorded in O.R. Book {random.randint(10000, 50000)}, "
        f"Page {random.randint(100, 9999)}, of the Public Records of {tx['county']} County, Florida.",

        f"8. Easement for public utilities recorded in O.R. Book {random.randint(10000, 50000)}, "
        f"Page {random.randint(100, 9999)}, of the Public Records of {tx['county']} County, Florida.",
    ]

    if tx.get('hoa_fee', 0) > 0:
        exceptions.append(
            f"9. Rights of the {tx.get('hoa', 'Homeowners Association')} under the Declaration "
            f"of Covenants, including the right to assess for common expenses."
        )

    for exc in exceptions:
        story.append(Paragraph(exc + '<br/><br/>', styles['Paragraph']))

    # Notes
    story.append(Paragraph('NOTES', styles['SectionHeader']))
    story.append(Paragraph(f"""
    A. Taxes for the year {date.today().year} are: ${tx.get('annual_property_tax', Decimal('8500')):,.2f}
       (Paid/Unpaid: Paid through current year)<br/><br/>

    B. Current mortgage(s) of record:<br/>
       Lender: {tx.get('current_lender', 'Bank of America, N.A.')}<br/>
       Original Amount: ${tx.get('current_mortgage_amount', tx['price'] * Decimal('0.70')):,.2f}<br/>
       Recorded: O.R. Book {random.randint(30000, 60000)}, Page {random.randint(100, 9999)}<br/><br/>

    C. This property {"IS" if tx.get('flood_zone', False) else "IS NOT"} located in a Special
       Flood Hazard Area (SFHA) as designated by FEMA.<br/><br/>

    D. According to the latest survey, there are no encroachments or boundary issues affecting
       the subject property.
    """, styles['Paragraph']))

    # Contact Information
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph('TITLE COMPANY CONTACT', styles['SectionHeader']))

    contact_data = [
        ['Company:', tx['title_company']],
        ['Address:', tx.get('title_company_address', '200 S. Biscayne Blvd, Suite 1500, Miami, FL 33131')],
        ['Title Officer:', tx.get('title_officer', 'Jennifer Martinez')],
        ['Phone:', tx.get('title_phone', '(305) 555-8900')],
        ['Email:', tx.get('title_email', 'jmartinez@titlecompany.com')],
        ['File Reference:', commitment_number],
    ]

    t = Table(contact_data, colWidths=[1.5*inch, 4.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    doc.build(story)
    print(f"Created: {filename}")


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Generate all sample documents with realistic Florida real estate data."""
    print("=" * 70)
    print("GENERATING REALISTIC FLORIDA REAL ESTATE DOCUMENTS")
    print("=" * 70)
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    # Realistic Florida transaction data - matches seed_data.py
    transactions = [
        {
            "id": "brickell_condo",
            "address": "1842 Brickell Ave, Unit 2405, Miami, FL 33129",
            "legal_description": "BRICKELL TOWER CONDO, UNIT 2405, ACCORDING TO THE DECLARATION "
                                "OF CONDOMINIUM THEREOF, AS RECORDED IN O.R. BOOK 28456, PAGE 1234, "
                                "OF THE PUBLIC RECORDS OF MIAMI-DADE COUNTY, FLORIDA",
            "parcel_id": "01-3210-045-2405",
            "county": "Miami-Dade",
            "price": Decimal("875000"),
            "buyer": "John M. Smith and Mary A. Smith, husband and wife",
            "seller": "Patricia M. Martinez, a single woman",
            "effective": date.today() - timedelta(days=25),
            "closing": date.today() + timedelta(days=35),
            "year_built": 2019,
            "square_feet": 1850,
            "bedrooms": 3,
            "bathrooms": "2.5",
            "hoa": "Brickell Tower Condominium Association, Inc.",
            "hoa_fee": Decimal("850"),
            "hoa_initiation_fee": Decimal("500"),
            "is_condo": True,
            "financing_type": "conventional",
            "loan_amount": Decimal("700000"),
            "interest_rate": Decimal("6.875"),
            "loan_term": 30,
            "financing_contingency_days": 30,
            "inspection_days": 15,
            "annual_property_tax": Decimal("9800"),
            "tax_year": 2025,
            "title_company": "First American Title Insurance Company",
            "escrow_agent": "First American Title Insurance Company",
            "escrow_agent_address": "200 S. Biscayne Blvd, Suite 1500, Miami, FL 33131",
            "escrow_agent_phone": "(305) 374-8900",
            "estimated_buyer_closing_costs": Decimal("18500"),
            "estimated_seller_closing_costs": Decimal("52500"),
            "listing_broker": "Sotheby's International Realty",
            "listing_agent": "Maria Elena Rodriguez",
            "listing_agent_license": "SL3456789",
            "selling_broker": "Douglas Elliman Real Estate",
            "selling_agent": "James R. Thompson",
            "selling_agent_license": "BK1234567",
            "has_pool": False,
            "hvac_age": 5,
            "roof_age": 5,
            "has_known_lead": False,
            "flood_zone": False,
            "reserve_balance": Decimal("2850000"),
            "required_reserves": Decimal("2500000"),
        },
        {
            "id": "coconut_grove",
            "address": "3456 Coconut Grove Dr, Miami, FL 33133",
            "legal_description": "LOT 15, BLOCK 3, COCONUT GROVE ESTATES, ACCORDING TO THE PLAT "
                                "THEREOF, AS RECORDED IN PLAT BOOK 45, PAGE 78, OF THE PUBLIC "
                                "RECORDS OF MIAMI-DADE COUNTY, FLORIDA",
            "parcel_id": "01-4123-015-0300",
            "county": "Miami-Dade",
            "price": Decimal("1250000"),
            "buyer": "Robert J. Johnson, a single man",
            "seller": "Richard A. Taylor and Susan B. Taylor, husband and wife",
            "effective": date.today() - timedelta(days=10),
            "closing": date.today() + timedelta(days=50),
            "year_built": 1962,
            "square_feet": 3200,
            "bedrooms": 4,
            "bathrooms": "3",
            "hoa": "Coconut Grove Estates Homeowners Association",
            "hoa_fee": Decimal("425"),
            "is_condo": False,
            "financing_type": "conventional",
            "loan_amount": Decimal("1000000"),
            "interest_rate": Decimal("7.125"),
            "loan_term": 30,
            "financing_contingency_days": 30,
            "inspection_days": 15,
            "annual_property_tax": Decimal("14200"),
            "tax_year": 2025,
            "title_company": "Old Republic National Title Insurance Company",
            "escrow_agent": "Old Republic National Title Insurance Company",
            "escrow_agent_address": "100 SE 2nd St, Suite 2800, Miami, FL 33131",
            "escrow_agent_phone": "(305) 358-5000",
            "estimated_buyer_closing_costs": Decimal("28500"),
            "estimated_seller_closing_costs": Decimal("75000"),
            "listing_broker": "Coldwell Banker Realty",
            "listing_agent": "Angela M. Davis",
            "listing_agent_license": "SL9876543",
            "selling_broker": "Compass Florida LLC",
            "selling_agent": "Michael Chen",
            "selling_agent_license": "BK5678901",
            "has_pool": True,
            "pool_size": "18x36",
            "pool_surface": "Pebble Tec",
            "hvac_age": 12,
            "roof_age": 8,
            "roof_type": "Concrete Tile",
            "foundation_type": "Concrete Block",
            "has_known_lead": False,  # Pre-1978 but remediated
            "has_lead_records": False,
            "flood_zone": False,
            "siding_type": "Stucco",
            "stories": 2,
            "garage_spaces": 2,
            "inspection_issues": [
                "Pool pump motor showing age - recommend monitoring",
                "Some original windows - consider upgrading for energy efficiency",
                "HVAC system 12 years old - near end of expected lifespan",
                "Minor grout deterioration in guest bathroom",
            ],
        },
        {
            "id": "tampa_downtown",
            "address": "401 E Jackson St, Unit 3201, Tampa, FL 33602",
            "legal_description": "UNIT 3201, SKYPOINT CONDOMINIUM, A CONDOMINIUM, ACCORDING TO "
                                "THE DECLARATION OF CONDOMINIUM THEREOF, AS RECORDED IN O.R. BOOK "
                                "19234, PAGE 567, OF THE PUBLIC RECORDS OF HILLSBOROUGH COUNTY, FLORIDA",
            "parcel_id": "A-28-29-18-4ZM-000000-00032.01",
            "county": "Hillsborough",
            "price": Decimal("485000"),
            "buyer": "Lisa Chen and David Chen, wife and husband",
            "seller": "Margaret T. Anderson, as Trustee of the Anderson Family Trust dated 01/15/2020",
            "effective": date.today() - timedelta(days=15),
            "closing": date.today() + timedelta(days=30),
            "year_built": 2020,
            "square_feet": 1450,
            "bedrooms": 2,
            "bathrooms": "2",
            "hoa": "SkyPoint Condominium Association, Inc.",
            "hoa_fee": Decimal("650"),
            "hoa_initiation_fee": Decimal("350"),
            "is_condo": True,
            "financing_type": "cash",
            "inspection_days": 10,
            "annual_property_tax": Decimal("5800"),
            "tax_year": 2025,
            "title_company": "Fidelity National Title Insurance Company",
            "escrow_agent": "Fidelity National Title Insurance Company",
            "escrow_agent_address": "400 N Tampa St, Suite 2400, Tampa, FL 33602",
            "escrow_agent_phone": "(813) 225-4500",
            "estimated_buyer_closing_costs": Decimal("8500"),
            "estimated_seller_closing_costs": Decimal("29000"),
            "has_pool": False,
            "hvac_age": 4,
            "roof_age": 4,
            "flood_zone": False,
        },
        {
            "id": "coral_gables",
            "address": "742 Alhambra Circle, Coral Gables, FL 33134",
            "legal_description": "LOT 8, BLOCK 12, CORAL GABLES SECTION D, ACCORDING TO THE PLAT "
                                "THEREOF, AS RECORDED IN PLAT BOOK 8, PAGE 33, OF THE PUBLIC "
                                "RECORDS OF MIAMI-DADE COUNTY, FLORIDA",
            "parcel_id": "03-4118-008-0120",
            "county": "Miami-Dade",
            "price": Decimal("1850000"),
            "buyer": "The Hernandez Family Trust dated 03/15/2024, Carlos Hernandez, Trustee",
            "seller": "William F. Morrison and Elizabeth K. Morrison, husband and wife",
            "effective": date.today() - timedelta(days=5),
            "closing": date.today() + timedelta(days=55),
            "year_built": 1948,
            "square_feet": 4100,
            "bedrooms": 5,
            "bathrooms": "4.5",
            "hoa": "Coral Gables Community Association",
            "hoa_fee": Decimal("175"),
            "is_condo": False,
            "financing_type": "conventional",
            "loan_amount": Decimal("1480000"),
            "interest_rate": Decimal("6.625"),
            "loan_term": 30,
            "financing_contingency_days": 45,
            "inspection_days": 20,
            "annual_property_tax": Decimal("22500"),
            "tax_year": 2025,
            "title_company": "Stewart Title Guaranty Company",
            "escrow_agent": "Stewart Title Guaranty Company",
            "escrow_agent_address": "333 SE 2nd Ave, Suite 2000, Miami, FL 33131",
            "escrow_agent_phone": "(305) 530-7600",
            "estimated_buyer_closing_costs": Decimal("42000"),
            "estimated_seller_closing_costs": Decimal("111000"),
            "has_pool": True,
            "pool_size": "20x40",
            "pool_surface": "Plaster",
            "hvac_age": 6,
            "roof_age": 15,
            "roof_type": "Clay Barrel Tile",
            "foundation_type": "Concrete Block",
            "has_known_lead": False,
            "has_lead_records": True,  # 1948 home, lead abatement records available
            "flood_zone": False,
            "siding_type": "Stucco (historic)",
            "stories": 2,
            "garage_spaces": 2,
            "additional_terms": [
                "Seller to complete pool resurfacing prior to closing",
                "All antique light fixtures to remain with property",
                "Buyer to have 30 days post-closing to complete historic renovation permits",
                "Coral Gables historic preservation review required for exterior modifications",
            ],
        },
        {
            "id": "naples_bay",
            "address": "8901 Bay Colony Dr, Unit 802, Naples, FL 34108",
            "legal_description": "UNIT 802, BAY COLONY CLUB CONDOMINIUM, ACCORDING TO THE "
                                "DECLARATION OF CONDOMINIUM THEREOF, AS RECORDED IN O.R. BOOK "
                                "2345, PAGE 890, OF THE PUBLIC RECORDS OF COLLIER COUNTY, FLORIDA",
            "parcel_id": "62351480008",
            "county": "Collier",
            "price": Decimal("2150000"),
            "buyer": "Oceanview Holdings LLC, a Delaware limited liability company",
            "seller": "Estate of Harold P. Winchester, deceased, by and through Patricia Winchester, "
                     "Personal Representative",
            "effective": date.today() - timedelta(days=20),
            "closing": date.today() + timedelta(days=40),
            "year_built": 2006,
            "square_feet": 3400,
            "bedrooms": 4,
            "bathrooms": "4",
            "hoa": "Bay Colony Club Condominium Association, Inc.",
            "hoa_fee": Decimal("1850"),
            "hoa_initiation_fee": Decimal("2500"),
            "is_condo": True,
            "financing_type": "cash",
            "inspection_days": 15,
            "annual_property_tax": Decimal("28500"),
            "tax_year": 2025,
            "title_company": "Chicago Title Insurance Company",
            "escrow_agent": "Chicago Title Insurance Company",
            "escrow_agent_address": "4001 Tamiami Trail N, Suite 200, Naples, FL 34103",
            "escrow_agent_phone": "(239) 649-5100",
            "estimated_buyer_closing_costs": Decimal("15000"),
            "estimated_seller_closing_costs": Decimal("129000"),
            "has_pool": False,  # Building amenities
            "hvac_age": 8,
            "roof_age": 8,
            "flood_zone": True,
            "has_flood_insurance": True,
            "reserve_balance": Decimal("4500000"),
            "required_reserves": Decimal("4000000"),
            "milestone_inspection_date": "September 2024",
            "sirs_date": "October 2024",
        },
    ]

    docs_created = 0

    for tx in transactions:
        print(f"\nGenerating documents for: {tx['address']}")
        print("-" * 50)

        # FAR/BAR AS-IS Contract
        create_farbar_asis_contract(f"contract_{tx['id']}.pdf", tx)
        docs_created += 1

        # Closing Disclosure (only for financed transactions)
        if tx.get('financing_type') in ['conventional', 'fha', 'va']:
            create_closing_disclosure(f"closing_disclosure_{tx['id']}.pdf", tx)
            docs_created += 1

        # Lead Paint Disclosure (for pre-1978 homes)
        if tx['year_built'] < 1978:
            create_lead_paint_disclosure(f"lead_disclosure_{tx['id']}.pdf", tx)
            docs_created += 1

        # Seller's Property Disclosure
        create_sellers_disclosure(f"sellers_disclosure_{tx['id']}.pdf", tx)
        docs_created += 1

        # HOA/Condo Disclosure
        if tx.get('hoa_fee', 0) > 0:
            create_hoa_disclosure(f"hoa_disclosure_{tx['id']}.pdf", tx)
            docs_created += 1

        # Home Inspection Report
        create_inspection_report(f"inspection_report_{tx['id']}.pdf", tx)
        docs_created += 1

        # Title Commitment
        create_title_commitment(f"title_commitment_{tx['id']}.pdf", tx)
        docs_created += 1

    print()
    print("=" * 70)
    print(f"GENERATION COMPLETE: {docs_created} documents created")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 70)

    # List all generated files
    print("\nGenerated files by transaction:")
    for tx in transactions:
        print(f"\n{tx['id'].upper()} - {tx['address'][:40]}...")
        for f in sorted(OUTPUT_DIR.glob(f'*_{tx["id"]}.pdf')):
            print(f"  • {f.name}")


if __name__ == "__main__":
    main()
