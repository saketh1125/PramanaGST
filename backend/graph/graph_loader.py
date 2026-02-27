import json
import logging
from typing import Dict, Any

from .connection import db
from . import node_creator
from . import relationship_creator

logger = logging.getLogger(__name__)

class GraphLoader:
    def __init__(self):
        self.stats = {
            "nodes_created": 0,
            "relationships_created": 0,
            "stubs_created": 0,
            "errors": 0
        }

    def load_batch_to_graph(self, batch_json_path: str) -> Dict[str, int]:
        """
        Orchestrates the ingestion of a single processed JSON batch file
        into the Neo4j Knowledge Graph.
        """
        logger.info(f"Loading batch: {batch_json_path}")
        
        try:
            with open(batch_json_path, 'r') as f:
                batch_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read batch file {batch_json_path}: {e}")
            self.stats["errors"] += 1
            return self.stats

        if batch_data.get("contract_version") != "1.0.0":
            logger.warning(f"Unsupported contract version or missing version in {batch_json_path}.")

        entities = batch_data.get("entities", {})
        
        with db.get_session() as session:
            # PHASE A: Create Nodes
            self._execute_node_creation(session, entities)
            
            # PHASE B: Create Relationships
            self._execute_relationship_creation(session, entities)
            
        logger.info(f"Batch {batch_json_path} loaded successfully: {self.stats}")
        return self.stats

    def _execute_node_creation(self, session, entities: Dict[str, list]):
        # Taxpayers
        for tp in entities.get("taxpayers", []):
            try:
                session.execute_write(node_creator.upsert_taxpayer, tp["entity_ref_id"], tp["data"])
                self.stats["nodes_created"] += 1
            except Exception as e:
                logger.error(f"Error creating taxpayer {tp.get('entity_ref_id')}: {e}")
                self.stats["errors"] += 1

        # Invoices and Observations
        for inv in entities.get("invoices", []):
            try:
                session.execute_write(node_creator.upsert_invoice, inv["entity_ref_id"], inv["data"])
                self.stats["nodes_created"] += 1
                
                # Create the observation linked to this invoice
                # Assuming source_record_id was injected in source_context or root at ingestion
                src_rec_id = inv.get("source_record_id") or inv["source_context"].get("source_record_id")
                
                session.execute_write(
                    node_creator.create_observation, 
                    inv["entity_ref_id"], 
                    src_rec_id,
                    inv["source_context"], 
                    inv["data"], 
                    inv["lineage"],
                    inv.get("validation_result", {})
                )
                self.stats["nodes_created"] += 1
            except Exception as e:
                logger.error(f"Error creating invoice/observation {inv.get('entity_ref_id')}: {e}")
                self.stats["errors"] += 1

        # Returns
        for ret in entities.get("returns", []):
            try:
                session.execute_write(node_creator.upsert_return, ret["entity_ref_id"], ret["data"])
                self.stats["nodes_created"] += 1
            except Exception as e:
                logger.error(f"Error creating return {ret.get('entity_ref_id')}: {e}")
                self.stats["errors"] += 1

        # Payments
        for pay in entities.get("payments", []):
            try:
                session.execute_write(node_creator.upsert_payment, pay["entity_ref_id"], pay["data"])
                self.stats["nodes_created"] += 1
            except Exception as e:
                logger.error(f"Error creating payment {pay.get('entity_ref_id')}: {e}")
                self.stats["errors"] += 1

        # IRNs
        for irn in entities.get("irns", []):
            try:
                session.execute_write(node_creator.upsert_irn, irn["entity_ref_id"], irn["data"])
                self.stats["nodes_created"] += 1
            except Exception as e:
                logger.error(f"Error creating irn {irn.get('entity_ref_id')}: {e}")
                self.stats["errors"] += 1

    def _execute_relationship_creation(self, session, entities: Dict[str, list]):
        
        for inv in entities.get("invoices", []):
            hints = inv.get("graph_hints", {}).get("foreign_keys", {})
            try:
                # 1. ISSUED_BY
                if "supplier_ref_id" in hints:
                    session.execute_write(relationship_creator.create_issued_by, inv["entity_ref_id"], hints["supplier_ref_id"])
                    self.stats["relationships_created"] += 1
                
                # 2. RECEIVED_BY (Can create stubs)
                if "recipient_ref_id" in hints and inv["data"].get("recipient_gstin"):
                    session.execute_write(relationship_creator.create_received_by, 
                                          inv["entity_ref_id"], 
                                          hints["recipient_ref_id"],
                                          inv["data"]["recipient_gstin"])
                    self.stats["relationships_created"] += 1

                # 3. REPORTED_IN or 4. RECORDED_IN depending on source
                src = inv["source_context"].get("source_system")
                if src in ["GSTR1", "GSTR2B"]:
                    # Expects return_ref_id in hints
                    if "return_ref_id" in hints:
                        # Need to synthesize the source_context mapping slightly for relations
                        inv_ctx = inv["source_context"]
                        inv_ctx["source_record_id"] = inv.get("source_record_id")
                        session.execute_write(relationship_creator.create_reported_in,
                                              inv["entity_ref_id"],
                                              hints["return_ref_id"],
                                              inv_ctx["reporter_gstin"],
                                              inv_ctx["reporting_period"],
                                              inv_ctx,
                                              inv["data"],
                                              src) # Return type is often same as source
                        self.stats["relationships_created"] += 1
                elif src == "PURCHASE_REGISTER":
                    # RECORDED_IN Buyer's Taxpayer Node
                    if "buyer_ref_id" in hints:
                        inv_ctx = inv["source_context"]
                        inv_ctx["source_record_id"] = inv.get("source_record_id")
                        session.execute_write(relationship_creator.create_recorded_in,
                                              inv["entity_ref_id"],
                                              hints["buyer_ref_id"],
                                              inv_ctx,
                                              inv["data"])
                        self.stats["relationships_created"] += 1

                # 5. LINKED_TO (E-Invoice handled below if IRN is present)
                # Usually we link from IRN entity up to Invoice, or vice versa if Invoice has an IRN ID
                if "irn_ref_id" in hints and inv["data"].get("irn"):
                     session.execute_write(relationship_creator.create_linked_to_irn,
                                          inv["entity_ref_id"],
                                          hints["irn_ref_id"],
                                          {'ack_number': None, 'ack_date': None, 'irn_status': 'ACTIVE'}) # Mock values as fallbacks
                     self.stats["relationships_created"] += 1
                     
                # 6. ADJUSTS
                if inv["data"].get("document_type") in ["CREDIT_NOTE", "DEBIT_NOTE"]:
                     if "original_invoice_ref_id" in hints:
                          session.execute_write(relationship_creator.create_adjusts, 
                                                inv["entity_ref_id"],
                                                hints["original_invoice_ref_id"],
                                                inv["data"])
                          self.stats["relationships_created"] += 1

            except Exception as e:
                logger.error(f"Error creating graph relationships for invoice {inv.get('entity_ref_id')}: {e}")
                self.stats["errors"] += 1

        # Return Relationships (FILED)
        for ret in entities.get("returns", []):
             hints = ret.get("graph_hints", {}).get("foreign_keys", {})
             if "taxpayer_ref_id" in hints:
                 try:
                     session.execute_write(relationship_creator.create_filed_by,
                                           hints["taxpayer_ref_id"],
                                           ret["entity_ref_id"],
                                           ret["data"])
                     self.stats["relationships_created"] += 1
                 except Exception as e:
                     logger.error(f"Error creating FILED rel for return {ret.get('entity_ref_id')}: {e}")
                     self.stats["errors"] += 1

        # Payment Relationships (PAID_TAX_IN)
        for pay in entities.get("payments", []):
             hints = pay.get("graph_hints", {}).get("foreign_keys", {})
             if "taxpayer_ref_id" in hints:
                  try:
                      session.execute_write(relationship_creator.create_paid_tax_in,
                                            hints["taxpayer_ref_id"],
                                            pay["entity_ref_id"],
                                            pay["data"])
                      self.stats["relationships_created"] += 1
                  except Exception as e:
                      logger.error(f"Error creating PAID_TAX_IN rel for payment {pay.get('entity_ref_id')}: {e}")
                      self.stats["errors"] += 1

        # IRN Relationships (LINKED_TO - from IRN side if not caught from invoice side)
        for irn in entities.get("irns", []):
             hints = irn.get("graph_hints", {}).get("foreign_keys", {})
             if "invoice_ref_id" in hints:
                  try:
                       session.execute_write(relationship_creator.create_linked_to_irn,
                                             hints["invoice_ref_id"],
                                             irn["entity_ref_id"],
                                             irn["data"])
                       self.stats["relationships_created"] += 1
                  except Exception as e:
                       logger.error(f"Error creating LINKED_TO rel for IRN {irn.get('entity_ref_id')}: {e}")
                       self.stats["errors"] += 1
                       
    def __del__(self):
        # We don't strictly need to close the singleton DB here, but it's good practice to close instances 
        pass
