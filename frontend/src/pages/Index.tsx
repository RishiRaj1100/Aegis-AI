import { useEffect } from "react";
import { Navbar } from "@/components/landing/Navbar";
import { HeroSection } from "@/components/landing/HeroSection";
import { CompareSection } from "@/components/landing/CompareSection";
import { HowItWorksSection } from "@/components/landing/HowItWorksSection";
import { TrustScoreSection } from "@/components/landing/TrustScoreSection";
import { UseCasesSection } from "@/components/landing/UseCasesSection";
import { StatsSection } from "@/components/landing/StatsSection";
import { PricingSection } from "@/components/landing/PricingSection";
import { Footer } from "@/components/landing/Footer";
import { prefetchLandingAuthRoutesOnce } from "@/utils/routePrefetch";

const Index = () => {
  useEffect(() => {
    prefetchLandingAuthRoutesOnce();
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <HeroSection />
      <UseCasesSection />
      <CompareSection />
      <HowItWorksSection />
      <TrustScoreSection />
      <StatsSection />
      <PricingSection />
      <Footer />
    </div>
  );
};

export default Index;
