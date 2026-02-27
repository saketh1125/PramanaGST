from .connection import db
import logging

logger = logging.getLogger(__name__)

def create_constraints():
    """
    Creates uniqueness constraints for entity_ref_id on all core labels,
    and source_record_id for SourceObservation to enforce idempotency.
    """
    queries = [
        # Uniqueness constraints
        "CREATE CONSTRAINT taxpayer_id IF NOT EXISTS FOR (t:Taxpayer) REQUIRE t.entity_ref_id IS UNIQUE",
        "CREATE CONSTRAINT invoice_id IF NOT EXISTS FOR (i:Invoice) REQUIRE i.entity_ref_id IS UNIQUE",
        "CREATE CONSTRAINT return_id IF NOT EXISTS FOR (r:Return) REQUIRE r.entity_ref_id IS UNIQUE",
        "CREATE CONSTRAINT payment_id IF NOT EXISTS FOR (p:Payment) REQUIRE p.entity_ref_id IS UNIQUE",
        "CREATE CONSTRAINT irn_id IF NOT EXISTS FOR (n:IRN) REQUIRE n.entity_ref_id IS UNIQUE",
        "CREATE CONSTRAINT observation_id IF NOT EXISTS FOR (o:SourceObservation) REQUIRE o.source_record_id IS UNIQUE",
        
        # Performance Indexes
        "CREATE INDEX taxpayer_gstin IF NOT EXISTS FOR (t:Taxpayer) ON (t.gstin)",
        "CREATE INDEX invoice_supplier IF NOT EXISTS FOR (i:Invoice) ON (i.supplier_gstin)",
        "CREATE INDEX invoice_recipient IF NOT EXISTS FOR (i:Invoice) ON (i.recipient_gstin)",
        "CREATE INDEX return_period IF NOT EXISTS FOR (r:Return) ON (r.return_period)",
        "CREATE INDEX payment_period IF NOT EXISTS FOR (p:Payment) ON (p.tax_period)"
    ]

    with db.get_session() as session:
        for q in queries:
            try:
                session.run(q)
                logger.info(f"Executed: {q.split(' IF NOT EXISTS')[0]}")
            except Exception as e:
                logger.error(f"Error creating constraint/index: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_constraints()
    print("Constraints and indexes applied successfully.")
