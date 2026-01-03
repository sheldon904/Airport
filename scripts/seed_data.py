"""
Seed script for populating Airport with realistic Florida real estate data.

Run with: python scripts/seed_data.py
"""

import asyncio
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from passlib.context import CryptContext
from sqlalchemy import text

from packages.db.session import AsyncSessionLocal
from packages.db.models import (
    OrganizationModel,
    UserModel,
    TransactionModel,
    DeadlineModel,
    ChecklistModel,
    ContactModel,
    CommunicationLogModel,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================================================
# REALISTIC FLORIDA DATA
# ============================================================================

FLORIDA_BROKERAGES = [
    {
        "name": "Sunshine State Realty Group",
        "license_number": "CQ1065432",
        "tier": "professional",
    },
    {
        "name": "Palm Coast Real Estate",
        "license_number": "CQ1058721",
        "tier": "starter",
    },
    {
        "name": "Atlantic Coast Properties",
        "license_number": "CQ1072345",
        "tier": "enterprise",
    },
]

FLORIDA_AGENTS = [
    # Brokerage 0 - Sunshine State
    {"name": "Maria Rodriguez", "email": "maria@sunshinerealty.com", "phone": "(305) 555-0101", "license": "SL3456789", "role": "broker"},
    {"name": "James Wilson", "email": "james@sunshinerealty.com", "phone": "(305) 555-0102", "license": "SL3456790", "role": "agent"},
    {"name": "Sarah Chen", "email": "sarah@sunshinerealty.com", "phone": "(305) 555-0103", "license": "SL3456791", "role": "agent"},
    # Brokerage 1 - Palm Coast
    {"name": "Michael Thompson", "email": "michael@palmcoast.com", "phone": "(904) 555-0201", "license": "SL3567890", "role": "admin"},
    {"name": "Jennifer Martinez", "email": "jennifer@palmcoast.com", "phone": "(904) 555-0202", "license": "SL3567891", "role": "agent"},
    # Brokerage 2 - Atlantic Coast
    {"name": "David Kim", "email": "david@atlanticcoast.com", "phone": "(813) 555-0301", "license": "SL3678901", "role": "broker"},
    {"name": "Emily Johnson", "email": "emily@atlanticcoast.com", "phone": "(813) 555-0302", "license": "SL3678902", "role": "agent"},
    {"name": "Robert Garcia", "email": "robert@atlanticcoast.com", "phone": "(813) 555-0303", "license": "SL3678903", "role": "agent"},
]

FLORIDA_PROPERTIES = [
    # Miami Area
    {"street": "1842 Brickell Ave", "unit": "Unit 2405", "city": "Miami", "zip": "33129", "county": "Miami-Dade", "price": 875000, "year": 2019, "is_condo": True, "is_hoa": True},
    {"street": "3456 Coconut Grove Dr", "unit": None, "city": "Miami", "zip": "33133", "county": "Miami-Dade", "price": 1250000, "year": 1962, "is_condo": False, "is_hoa": True},
    {"street": "789 Ocean Drive", "unit": "PH 1", "city": "Miami Beach", "zip": "33139", "county": "Miami-Dade", "price": 2400000, "year": 2021, "is_condo": True, "is_hoa": True},
    # Fort Lauderdale Area
    {"street": "2100 E Las Olas Blvd", "unit": "Suite 1802", "city": "Fort Lauderdale", "zip": "33301", "county": "Broward", "price": 695000, "year": 2015, "is_condo": True, "is_hoa": True},
    {"street": "5421 NE 21st Ave", "unit": None, "city": "Fort Lauderdale", "zip": "33308", "county": "Broward", "price": 525000, "year": 1978, "is_condo": False, "is_hoa": False},
    # Tampa Area
    {"street": "401 E Jackson St", "unit": "Unit 3201", "city": "Tampa", "zip": "33602", "county": "Hillsborough", "price": 485000, "year": 2020, "is_condo": True, "is_hoa": True},
    {"street": "3789 Bayshore Blvd", "unit": None, "city": "Tampa", "zip": "33629", "county": "Hillsborough", "price": 1875000, "year": 1935, "is_condo": False, "is_hoa": False},
    {"street": "1256 S Howard Ave", "unit": None, "city": "Tampa", "zip": "33606", "county": "Hillsborough", "price": 625000, "year": 2005, "is_condo": False, "is_hoa": True},
    # Orlando Area
    {"street": "8901 International Dr", "unit": "Unit 512", "city": "Orlando", "zip": "32819", "county": "Orange", "price": 289000, "year": 2018, "is_condo": True, "is_hoa": True},
    {"street": "4521 Lake Nona Blvd", "unit": None, "city": "Orlando", "zip": "32827", "county": "Orange", "price": 545000, "year": 2022, "is_condo": False, "is_hoa": True},
    {"street": "1789 Park Ave", "unit": None, "city": "Winter Park", "zip": "32789", "county": "Orange", "price": 895000, "year": 1948, "is_condo": False, "is_hoa": False},
    # Jacksonville Area
    {"street": "1 Independent Dr", "unit": "Unit 801", "city": "Jacksonville", "zip": "32202", "county": "Duval", "price": 375000, "year": 2017, "is_condo": True, "is_hoa": True},
    {"street": "4523 San Jose Blvd", "unit": None, "city": "Jacksonville", "zip": "32207", "county": "Duval", "price": 425000, "year": 1985, "is_condo": False, "is_hoa": True},
    # Naples Area
    {"street": "9087 Gulf Shore Dr", "unit": "Unit 1501", "city": "Naples", "zip": "34108", "county": "Collier", "price": 1650000, "year": 2016, "is_condo": True, "is_hoa": True},
    {"street": "2345 Pine Ridge Rd", "unit": None, "city": "Naples", "zip": "34109", "county": "Collier", "price": 975000, "year": 2010, "is_condo": False, "is_hoa": True},
]

PARTY_NAMES = {
    "buyers": [
        ("John & Mary Smith", "johnsmith@email.com", "(305) 555-1001"),
        ("Robert Johnson", "rjohnson@email.com", "(813) 555-1002"),
        ("Lisa & David Chen", "chenl@email.com", "(407) 555-1003"),
        ("Amanda Torres", "atorres@email.com", "(904) 555-1004"),
        ("William & Karen Brown", "wbrown@email.com", "(954) 555-1005"),
        ("Christopher Lee", "clee@email.com", "(239) 555-1006"),
        ("Jennifer & Michael Davis", "jdavis@email.com", "(305) 555-1007"),
        ("Thomas Wilson", "twilson@email.com", "(813) 555-1008"),
    ],
    "sellers": [
        ("Patricia Martinez", "pmartinez@email.com", "(305) 555-2001"),
        ("Richard & Susan Taylor", "rtaylor@email.com", "(954) 555-2002"),
        ("Margaret Anderson", "manderson@email.com", "(407) 555-2003"),
        ("James & Barbara White", "jwhite@email.com", "(813) 555-2004"),
        ("Elizabeth Jackson", "ejackson@email.com", "(904) 555-2005"),
        ("Frank & Nancy Harris", "fharris@email.com", "(239) 555-2006"),
        ("George Thompson", "gthompson@email.com", "(305) 555-2007"),
        ("Dorothy & Paul Robinson", "drobinson@email.com", "(954) 555-2008"),
    ],
}

TITLE_COMPANIES = [
    ("First American Title Insurance", "closings@firstam-fl.com", "(305) 555-3001"),
    ("Fidelity National Title", "fl-closings@fntic.com", "(813) 555-3002"),
    ("Stewart Title Guaranty", "florida@stewart.com", "(407) 555-3003"),
    ("Old Republic Title", "closings@oldrepublic-fl.com", "(904) 555-3004"),
]

LENDERS = [
    ("Bank of America Mortgage", "mortgages@bofa.com", "(800) 555-4001"),
    ("Wells Fargo Home Mortgage", "homeloans@wellsfargo.com", "(800) 555-4002"),
    ("Quicken Loans", "florida@quickenloans.com", "(800) 555-4003"),
    ("PNC Mortgage", "pncmortgage@pnc.com", "(800) 555-4004"),
    ("Chase Home Lending", "homelending@chase.com", "(800) 555-4005"),
]

TRANSACTION_STATUSES = ["draft", "active", "under_contract", "pending", "closed", "cancelled"]
TRANSACTION_TYPES = ["purchase", "sale", "dual_agency"]

# Florida Statutory Deadlines
FLORIDA_DEADLINES = [
    {"type": "statutory", "name": "Seller's Property Disclosure", "days_from_effective": 3, "statute": "F.S. 689.25"},
    {"type": "statutory", "name": "Radon Gas Disclosure", "days_from_effective": 0, "statute": "F.S. 404.056"},
    {"type": "statutory", "name": "Lead-Based Paint Disclosure", "days_from_effective": 10, "statute": "42 U.S.C. 4852d", "pre_1978_only": True},
    {"type": "statutory", "name": "HOA Disclosure", "days_from_effective": 3, "statute": "F.S. 720.401", "hoa_only": True},
    {"type": "statutory", "name": "Condo Documents Delivery", "days_from_effective": 3, "statute": "F.S. 718.503", "condo_only": True},
    {"type": "statutory", "name": "Condo Rescission Period", "days_from_effective": 15, "statute": "F.S. 718.503", "condo_only": True},
    {"type": "contingency", "name": "Inspection Period", "days_from_effective": 15, "statute": None},
    {"type": "contingency", "name": "Financing Contingency", "days_from_effective": 30, "statute": None, "financed_only": True},
    {"type": "contingency", "name": "Appraisal Contingency", "days_from_effective": 21, "statute": None, "financed_only": True},
    {"type": "trid", "name": "Loan Estimate Delivery", "days_from_effective": 3, "statute": "12 CFR 1026.19", "financed_only": True},
    {"type": "trid", "name": "Closing Disclosure Delivery", "days_before_closing": 3, "statute": "12 CFR 1026.19(f)", "financed_only": True},
]


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


async def clear_existing_data(session):
    """Clear existing seed data (but not the user's own data)."""
    print("Clearing existing seed data...")
    # We'll only clear data from organizations we're about to create
    # In a real scenario, you might want to be more selective
    await session.execute(text("DELETE FROM communication_log WHERE organization_id IN (SELECT id FROM organizations WHERE license_number LIKE 'CQ%')"))
    await session.execute(text("DELETE FROM contacts WHERE organization_id IN (SELECT id FROM organizations WHERE license_number LIKE 'CQ%')"))
    await session.execute(text("DELETE FROM audit_logs WHERE transaction_id IN (SELECT id FROM transactions WHERE organization_id IN (SELECT id FROM organizations WHERE license_number LIKE 'CQ%'))"))
    await session.execute(text("DELETE FROM deadlines WHERE transaction_id IN (SELECT id FROM transactions WHERE organization_id IN (SELECT id FROM organizations WHERE license_number LIKE 'CQ%'))"))
    await session.execute(text("DELETE FROM checklists WHERE transaction_id IN (SELECT id FROM transactions WHERE organization_id IN (SELECT id FROM organizations WHERE license_number LIKE 'CQ%'))"))
    await session.execute(text("DELETE FROM documents WHERE transaction_id IN (SELECT id FROM transactions WHERE organization_id IN (SELECT id FROM organizations WHERE license_number LIKE 'CQ%'))"))
    await session.execute(text("DELETE FROM transactions WHERE organization_id IN (SELECT id FROM organizations WHERE license_number LIKE 'CQ%')"))
    await session.execute(text("DELETE FROM users WHERE organization_id IN (SELECT id FROM organizations WHERE license_number LIKE 'CQ%')"))
    await session.execute(text("DELETE FROM organizations WHERE license_number LIKE 'CQ%'"))
    await session.commit()
    print("Cleared existing seed data.")


async def seed_organizations(session) -> list[OrganizationModel]:
    """Create organizations."""
    print("Creating organizations...")
    orgs = []
    for brokerage in FLORIDA_BROKERAGES:
        org = OrganizationModel(
            id=uuid4(),
            name=brokerage["name"],
            license_number=brokerage["license_number"],
            state="FL",
            subscription_tier=brokerage["tier"],
            subscription_status="active",
            settings={
                "default_inspection_days": 15,
                "default_financing_days": 30,
                "auto_create_deadlines": True,
            },
            compliance_config={
                "require_lead_paint": True,
                "require_hoa_disclosure": True,
                "require_condo_docs": True,
            },
        )
        session.add(org)
        orgs.append(org)
    await session.flush()
    print(f"Created {len(orgs)} organizations.")
    return orgs


async def seed_users(session, orgs: list[OrganizationModel]) -> list[UserModel]:
    """Create users for each organization."""
    print("Creating users...")
    users = []
    agent_idx = 0
    org_assignments = [3, 2, 3]  # Number of agents per org

    for org_idx, org in enumerate(orgs):
        for _ in range(org_assignments[org_idx]):
            agent = FLORIDA_AGENTS[agent_idx]
            user = UserModel(
                id=uuid4(),
                organization_id=org.id,
                email=agent["email"],
                hashed_password=hash_password("TestPassword123"),  # Same password for all test users
                full_name=agent["name"],
                role=agent["role"],
                phone=agent["phone"],
                license_number=agent["license"],
                notification_preferences={
                    "email_deadlines": True,
                    "email_documents": True,
                    "sms_urgent": False,
                },
                is_active=True,
                email_verified=True,
            )
            session.add(user)
            users.append(user)
            agent_idx += 1

    await session.flush()
    print(f"Created {len(users)} users.")
    return users


async def seed_contacts(session, orgs: list[OrganizationModel]) -> list[ContactModel]:
    """Create contacts for each organization."""
    print("Creating contacts...")
    contacts = []

    for org in orgs:
        # Add buyers as contacts
        for name, email, phone in PARTY_NAMES["buyers"][:4]:
            contact = ContactModel(
                id=uuid4(),
                organization_id=org.id,
                full_name=name,
                email=email,
                phone=phone,
                contact_type="buyer",
                source="transaction",
                transaction_count=random.randint(1, 3),
                tags=["active", "qualified"],
            )
            session.add(contact)
            contacts.append(contact)

        # Add sellers as contacts
        for name, email, phone in PARTY_NAMES["sellers"][:4]:
            contact = ContactModel(
                id=uuid4(),
                organization_id=org.id,
                full_name=name,
                email=email,
                phone=phone,
                contact_type="seller",
                source="transaction",
                transaction_count=random.randint(1, 2),
                tags=["past_client"],
            )
            session.add(contact)
            contacts.append(contact)

        # Add title companies
        for name, email, phone in TITLE_COMPANIES[:2]:
            contact = ContactModel(
                id=uuid4(),
                organization_id=org.id,
                full_name=name,
                email=email,
                phone=phone,
                contact_type="title_company",
                company=name,
                source="manual",
                transaction_count=random.randint(5, 20),
                tags=["preferred_vendor"],
            )
            session.add(contact)
            contacts.append(contact)

        # Add lenders
        for name, email, phone in LENDERS[:2]:
            contact = ContactModel(
                id=uuid4(),
                organization_id=org.id,
                full_name=name,
                email=email,
                phone=phone,
                contact_type="lender",
                company=name,
                source="manual",
                transaction_count=random.randint(10, 30),
                tags=["preferred_lender"],
            )
            session.add(contact)
            contacts.append(contact)

    await session.flush()
    print(f"Created {len(contacts)} contacts.")
    return contacts


async def seed_transactions(session, orgs: list[OrganizationModel], users: list[UserModel]) -> list[TransactionModel]:
    """Create realistic transactions."""
    print("Creating transactions...")
    transactions = []

    # Map users to their organizations
    org_users = {}
    for user in users:
        if user.organization_id not in org_users:
            org_users[user.organization_id] = []
        org_users[user.organization_id].append(user)

    property_idx = 0
    buyer_idx = 0
    seller_idx = 0

    for org in orgs:
        org_user_list = org_users[org.id]
        num_transactions = 5 if org.subscription_tier == "enterprise" else 3

        for i in range(num_transactions):
            prop = FLORIDA_PROPERTIES[property_idx % len(FLORIDA_PROPERTIES)]
            property_idx += 1

            buyer = PARTY_NAMES["buyers"][buyer_idx % len(PARTY_NAMES["buyers"])]
            buyer_idx += 1
            seller = PARTY_NAMES["sellers"][seller_idx % len(PARTY_NAMES["sellers"])]
            seller_idx += 1

            title_co = random.choice(TITLE_COMPANIES)
            lender = random.choice(LENDERS)

            # Determine transaction status and dates
            status = random.choices(
                TRANSACTION_STATUSES,
                weights=[0.05, 0.25, 0.30, 0.20, 0.15, 0.05]
            )[0]

            today = date.today()
            if status == "closed":
                effective_date = today - timedelta(days=random.randint(45, 90))
                closing_date = effective_date + timedelta(days=random.randint(30, 45))
            elif status == "cancelled":
                effective_date = today - timedelta(days=random.randint(15, 45))
                closing_date = effective_date + timedelta(days=45)
            elif status == "draft":
                effective_date = None
                closing_date = None
            else:
                effective_date = today - timedelta(days=random.randint(5, 25))
                closing_date = today + timedelta(days=random.randint(15, 45))

            is_financed = random.random() > 0.15  # 85% financed

            # Build address
            address = {
                "street": prop["street"],
                "city": prop["city"],
                "state": "FL",
                "zip": prop["zip"],
                "county": prop["county"],
            }
            if prop["unit"]:
                address["unit"] = prop["unit"]

            # Build parties list
            parties = [
                {
                    "role": "buyer",
                    "name": buyer[0],
                    "email": buyer[1],
                    "phone": buyer[2],
                },
                {
                    "role": "seller",
                    "name": seller[0],
                    "email": seller[1],
                    "phone": seller[2],
                },
                {
                    "role": "title_company",
                    "name": title_co[0],
                    "email": title_co[1],
                    "phone": title_co[2],
                },
            ]

            if is_financed:
                parties.append({
                    "role": "lender",
                    "name": lender[0],
                    "email": lender[1],
                    "phone": lender[2],
                })

            # Calculate priority score
            priority_score = 50
            if status in ["active", "under_contract"]:
                if closing_date and (closing_date - today).days < 14:
                    priority_score = 90
                elif closing_date and (closing_date - today).days < 30:
                    priority_score = 75

            health_status = "on_track"
            if status == "cancelled":
                health_status = "cancelled"
            elif status == "closed":
                health_status = "completed"
            elif priority_score > 80:
                health_status = "at_risk"

            transaction = TransactionModel(
                id=uuid4(),
                organization_id=org.id,
                created_by=random.choice(org_user_list).id,
                status=status,
                transaction_type=random.choice(TRANSACTION_TYPES),
                property_address=address,
                purchase_price=Decimal(str(prop["price"])),
                year_built=prop["year"],
                is_hoa=prop["is_hoa"],
                is_condo=prop["is_condo"],
                is_financed=is_financed,
                effective_date=effective_date,
                closing_date=closing_date,
                parties=parties,
                notes=f"Transaction for {address['street']}, {address['city']}",
                priority_score=priority_score,
                health_status=health_status,
            )
            session.add(transaction)
            transactions.append(transaction)

    await session.flush()
    print(f"Created {len(transactions)} transactions.")
    return transactions


async def seed_deadlines(session, transactions: list[TransactionModel]) -> list[DeadlineModel]:
    """Create deadlines for transactions."""
    print("Creating deadlines...")
    deadlines = []

    for tx in transactions:
        if tx.status == "draft" or not tx.effective_date:
            continue

        for deadline_template in FLORIDA_DEADLINES:
            # Check conditions
            if deadline_template.get("pre_1978_only") and tx.year_built and tx.year_built >= 1978:
                continue
            if deadline_template.get("hoa_only") and not tx.is_hoa:
                continue
            if deadline_template.get("condo_only") and not tx.is_condo:
                continue
            if deadline_template.get("financed_only") and not tx.is_financed:
                continue

            # Calculate due date
            if "days_from_effective" in deadline_template:
                due_date = tx.effective_date + timedelta(days=deadline_template["days_from_effective"])
            elif "days_before_closing" in deadline_template and tx.closing_date:
                due_date = tx.closing_date - timedelta(days=deadline_template["days_before_closing"])
            else:
                continue

            # Determine status
            today = date.today()
            if tx.status == "closed":
                status = "completed"
                completed_at = datetime.combine(due_date, datetime.min.time())
            elif tx.status == "cancelled":
                status = "cancelled"
                completed_at = None
            elif due_date < today:
                status = random.choice(["completed", "overdue"])
                completed_at = datetime.combine(due_date, datetime.min.time()) if status == "completed" else None
            elif due_date <= today + timedelta(days=3):
                status = "due_soon"
                completed_at = None
            else:
                status = "upcoming"
                completed_at = None

            deadline = DeadlineModel(
                id=uuid4(),
                transaction_id=tx.id,
                deadline_type=deadline_template["type"],
                name=deadline_template["name"],
                description=f"{deadline_template['name']} - {deadline_template.get('statute', 'Contract contingency')}",
                due_date=due_date,
                status=status,
                reminder_days=[7, 3, 1],
                completed_at=completed_at,
                notes=f"Statute: {deadline_template.get('statute', 'N/A')}" if deadline_template.get('statute') else None,
            )
            session.add(deadline)
            deadlines.append(deadline)

    await session.flush()
    print(f"Created {len(deadlines)} deadlines.")
    return deadlines


async def seed_communications(session, transactions: list[TransactionModel], orgs: list[OrganizationModel]) -> list[CommunicationLogModel]:
    """Create communication logs for transactions."""
    print("Creating communication logs...")
    communications = []

    topics = [
        "inspection_scheduling",
        "document_request",
        "closing_coordination",
        "status_update",
        "contingency_resolution",
        "title_issue",
        "financing_update",
    ]

    for tx in transactions:
        if tx.status in ["draft", "cancelled"]:
            continue

        num_comms = random.randint(2, 8)
        for i in range(num_comms):
            buyer = next((p for p in tx.parties if p["role"] == "buyer"), None)
            seller = next((p for p in tx.parties if p["role"] == "seller"), None)
            title = next((p for p in tx.parties if p["role"] == "title_company"), None)

            direction = random.choice(["inbound", "outbound"])
            topic = random.choice(topics)

            if direction == "outbound":
                sender = "agent@brokerage.com"
                if topic in ["closing_coordination", "title_issue"]:
                    recipients = [title["email"]] if title else []
                else:
                    recipients = [buyer["email"]] if buyer else []
            else:
                if topic == "financing_update":
                    sender = "lender@bank.com"
                elif topic == "title_issue":
                    sender = title["email"] if title else "title@company.com"
                else:
                    sender = buyer["email"] if buyer else "client@email.com"
                recipients = ["agent@brokerage.com"]

            subjects = {
                "inspection_scheduling": "RE: Home Inspection Scheduling",
                "document_request": "Document Request - {address}",
                "closing_coordination": "Closing Coordination - {address}",
                "status_update": "Transaction Status Update",
                "contingency_resolution": "RE: Contingency Period",
                "title_issue": "Title Commitment Review",
                "financing_update": "Loan Status Update",
            }

            address = tx.property_address.get("street", "Property")
            subject = subjects.get(topic, "RE: Transaction").format(address=address)

            comm = CommunicationLogModel(
                id=uuid4(),
                transaction_id=tx.id,
                organization_id=tx.organization_id,
                direction=direction,
                channel="email",
                subject=subject,
                body_preview=f"This is a communication regarding {topic.replace('_', ' ')} for the property at {address}...",
                sender=sender,
                recipients=recipients,
                topic=topic,
                status="sent" if direction == "outbound" else "received",
                sent_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            )
            session.add(comm)
            communications.append(comm)

    await session.flush()
    print(f"Created {len(communications)} communication logs.")
    return communications


async def seed_checklists(session, transactions: list[TransactionModel]) -> list[ChecklistModel]:
    """Create checklists for transactions."""
    print("Creating checklists...")
    checklists = []

    base_items = [
        {"name": "Contract Executed", "category": "contract", "required": True},
        {"name": "Earnest Money Deposited", "category": "contract", "required": True},
        {"name": "Seller's Disclosure Received", "category": "disclosure", "required": True},
        {"name": "Property Inspection Completed", "category": "inspection", "required": False},
        {"name": "Appraisal Ordered", "category": "financing", "required": False},
        {"name": "Title Commitment Received", "category": "title", "required": True},
        {"name": "Survey Ordered", "category": "title", "required": False},
        {"name": "Homeowner's Insurance Bound", "category": "insurance", "required": True},
        {"name": "Final Walkthrough Completed", "category": "closing", "required": True},
        {"name": "Closing Disclosure Signed", "category": "closing", "required": True},
    ]

    for tx in transactions:
        if tx.status == "draft":
            continue

        items = []
        for item in base_items:
            # Skip financing items if cash deal
            if item["category"] == "financing" and not tx.is_financed:
                continue

            # Determine completion status based on transaction status
            if tx.status == "closed":
                completed = True
            elif tx.status == "cancelled":
                completed = False
            else:
                completed = random.random() > 0.4 if item["required"] else random.random() > 0.6

            items.append({
                "id": str(uuid4()),
                "name": item["name"],
                "category": item["category"],
                "required": item["required"],
                "completed": completed,
                "completed_at": datetime.utcnow().isoformat() if completed else None,
                "notes": None,
            })

        # Add HOA items if applicable
        if tx.is_hoa:
            items.append({
                "id": str(uuid4()),
                "name": "HOA Disclosure Received",
                "category": "hoa",
                "required": True,
                "completed": tx.status == "closed" or random.random() > 0.3,
                "completed_at": datetime.utcnow().isoformat() if tx.status == "closed" else None,
                "notes": None,
            })
            items.append({
                "id": str(uuid4()),
                "name": "HOA Estoppel Letter",
                "category": "hoa",
                "required": True,
                "completed": tx.status == "closed" or random.random() > 0.5,
                "completed_at": datetime.utcnow().isoformat() if tx.status == "closed" else None,
                "notes": None,
            })

        # Add condo items if applicable
        if tx.is_condo:
            items.append({
                "id": str(uuid4()),
                "name": "Condo Association Documents",
                "category": "condo",
                "required": True,
                "completed": tx.status == "closed" or random.random() > 0.3,
                "completed_at": datetime.utcnow().isoformat() if tx.status == "closed" else None,
                "notes": None,
            })

        template_id = "florida_residential_purchase"
        if tx.is_condo:
            template_id = "florida_condo_purchase"

        checklist = ChecklistModel(
            id=uuid4(),
            transaction_id=tx.id,
            template_id=template_id,
            items=items,
        )
        session.add(checklist)
        checklists.append(checklist)

    await session.flush()
    print(f"Created {len(checklists)} checklists.")
    return checklists


async def main():
    """Main seed function."""
    print("=" * 60)
    print("AIRPORT DATABASE SEEDER")
    print("Populating with realistic Florida real estate data")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        try:
            # Clear existing seed data
            await clear_existing_data(session)

            # Seed data
            orgs = await seed_organizations(session)
            users = await seed_users(session, orgs)
            contacts = await seed_contacts(session, orgs)
            transactions = await seed_transactions(session, orgs, users)
            deadlines = await seed_deadlines(session, transactions)
            communications = await seed_communications(session, transactions, orgs)
            checklists = await seed_checklists(session, transactions)

            # Commit all changes
            await session.commit()

            print("=" * 60)
            print("SEED COMPLETE!")
            print("=" * 60)
            print(f"Organizations: {len(orgs)}")
            print(f"Users: {len(users)}")
            print(f"Contacts: {len(contacts)}")
            print(f"Transactions: {len(transactions)}")
            print(f"Deadlines: {len(deadlines)}")
            print(f"Communications: {len(communications)}")
            print(f"Checklists: {len(checklists)}")
            print("=" * 60)
            print("\nTest Login Credentials:")
            print("-" * 40)
            for agent in FLORIDA_AGENTS[:3]:
                print(f"Email: {agent['email']}")
                print(f"Password: TestPassword123")
                print(f"Role: {agent['role']}")
                print("-" * 40)

        except Exception as e:
            await session.rollback()
            print(f"ERROR: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
