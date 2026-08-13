"use client";

import type { ComponentType } from "react";
import { PersonalShopperPanel } from "./personal-shopper-panel";
import { RecsysPanel } from "./recsys-panel";
import { ContentGeneratorPanel } from "./content-generator-panel";
import { SellerCoachPanel } from "./seller-coach-panel";
import { ReviewIntelligencePanel } from "./review-intelligence-panel";
import { SegmentationPanel } from "./segmentation-panel";
import { DynamicPricingPanel } from "./dynamic-pricing-panel";
import { CustomerRiskPanel } from "./customer-risk-panel";
import { CustomerJourneyPanel } from "./customer-journey-panel";
import { InventoryAlertPanel } from "./inventory-alert-panel";
import { SupplyChainPanel } from "./supply-chain-panel";
import { FlashSalePanel } from "./flash-sale-panel";
import { ProductKnowledgePanel } from "./product-knowledge-panel";
import { MarketIntelligencePanel } from "./market-intelligence-panel";
import { CreatorPerformancePanel } from "./creator-performance-panel";
import { DecisionIntelligencePanel } from "./decision-intelligence-panel";
import { ProductGraphPanel } from "./product-graph-panel";
import { CopilotPanel } from "./copilot-panel";
import { DailyBriefingPanel } from "./daily-briefing-panel";
import { RestockPlannerPanel } from "./restock-planner-panel";
import { MarketplacePanel } from "./marketplace-panel";

/** Maps a feature slug to its live panel. Keep in sync with IMPLEMENTED in lib/nav. */
const PANELS: Record<string, ComponentType> = {
  copilot: CopilotPanel,
  "daily-briefing": DailyBriefingPanel,
  "personal-shopper": PersonalShopperPanel,
  recsys: RecsysPanel,
  "content-generator": ContentGeneratorPanel,
  "seller-coach": SellerCoachPanel,
  "review-intelligence": ReviewIntelligencePanel,
  segmentation: SegmentationPanel,
  "dynamic-pricing": DynamicPricingPanel,
  "customer-risk": CustomerRiskPanel,
  "customer-journey": CustomerJourneyPanel,
  "sentiment-alert": InventoryAlertPanel,
  "supply-chain": SupplyChainPanel,
  "emotion-sale": FlashSalePanel,
  "product-knowledge": ProductKnowledgePanel,
  "market-intelligence": MarketIntelligencePanel,
  "creator-performance": CreatorPerformancePanel,
  "decision-intelligence": DecisionIntelligencePanel,
  "product-graph": ProductGraphPanel,
  "restock-planner": RestockPlannerPanel,
  marketplace: MarketplacePanel,
};

export function FeaturePanel({ slug }: { slug: string }) {
  const Panel = PANELS[slug];
  return Panel ? <Panel /> : null;
}
