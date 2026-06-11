import { Navigation } from "@/components/navigation";
import { Hero } from "@/components/hero";
import { TrustedBy } from "@/components/trusted-by";
import { Problem } from "@/components/problem";
import { Solution } from "@/components/solution";
import { Features } from "@/components/features";
import { Architecture } from "@/components/architecture";
import { DashboardPreview } from "@/components/dashboard-preview";
import { DeveloperExperience } from "@/components/developer-experience";
import { Comparison } from "@/components/comparison";
import { ProductionReadiness } from "@/components/production-readiness";
import { UseCases } from "@/components/use-cases";
import { Testimonials } from "@/components/testimonials";
import { FAQ } from "@/components/faq";
import { CTAFooter } from "@/components/cta-footer";

export default function Home() {
  return (
    <main>
      <Navigation />
      <Hero />
      <TrustedBy />
      <Problem />
      <Solution />
      <Features />
      <Architecture />
      <DashboardPreview />
      <DeveloperExperience />
      <Comparison />
      <ProductionReadiness />
      <UseCases />
      <Testimonials />
      <FAQ />
      <CTAFooter />
    </main>
  );
}
