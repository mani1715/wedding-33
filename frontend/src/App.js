import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import { AuthProvider } from './context/AuthContext';
import { UserAuthProvider } from './context/UserAuthContext';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingFallback from './components/LoadingFallback';

// PHASE 2: CODE SPLITTING - Lazy load all heavy pages for better initial load
const LandingPage = lazy(() => import('./pages/LandingPage'));

// Public pages - Lazy loaded
const AuthCallback = lazy(() => import('./pages/AuthCallback'));
const LuxuryPreview = lazy(() => import('./pages/LuxuryPreview'));
const LuxuryPublicInvitation = lazy(() => import('./pages/LuxuryPublicInvitation'));
const SaveTheDatePage = lazy(() => import('./pages/SaveTheDatePage'));
const ThemeInvitationPreview = lazy(() => import('./pages/ThemeInvitationPreview'));
const CoupleAccess = lazy(() => import('./pages/CoupleAccess'));
const ThemeShowroom = lazy(() => import('./pages/ThemeShowroom'));
const KeralaDesignGallery = lazy(() => import('./pages/KeralaDesignGallery'));
const ThemeDesignGallery = lazy(() => import('./pages/ThemeDesignGallery'));
const ThemeEventPicker = lazy(() => import('./pages/ThemeEventPicker'));
const EventDesignPicker = lazy(() => import('./pages/EventDesignPicker'));
const DesignFullPreview = lazy(() => import('./pages/DesignFullPreview'));

// Photographer admin - Lazy loaded
const AdminLogin = lazy(() => import('./pages/AdminLogin'));
const AdminSignup = lazy(() => import('./pages/AdminSignup'));
const LuxuryDashboard = lazy(() => import('./pages/LuxuryDashboard'));
const TrashBinPage = lazy(() => import('./pages/TrashBinPage'));
const LuxuryProfileForm = lazy(() => import('./pages/LuxuryProfileForm'));
const EventInvitationWizard = lazy(() => import('./pages/EventInvitationWizard'));
const EventCategorySelector = lazy(() => import('./pages/EventCategorySelector'));
const CelebrationProfileForm = lazy(() => import('./pages/CelebrationProfileForm'));
const CelebrationPurchaseWizard = lazy(() => import('./pages/CelebrationPurchaseWizard'));
// 2026-09 — Live sample invitation preview for non-wedding categories.
// Lets a homepage visitor experience the full invitation (cinematic opening
// + features playing live) before they buy.
const CelebrationInvitationPreview = lazy(() => import('./pages/CelebrationInvitationPreview'));

// Super admin - Lazy loaded
const SuperAdminLogin = lazy(() => import('./pages/SuperAdminLogin'));
const LuxurySuperAdminDashboard = lazy(() => import('./pages/LuxurySuperAdminDashboard'));
const SuperAdminPricingHub = lazy(() => import('./pages/SuperAdminPricingHub'));
const SuperAdminGiftCodes = lazy(() => import('./pages/SuperAdminGiftCodes'));
const SuperAdminExpiryTiers = lazy(() => import('./pages/SuperAdminExpiryTiers'));
const PurchaseFlowPage = lazy(() => import('./pages/PurchaseFlowPage'));
const AccountCreditsPage = lazy(() => import('./pages/AccountCreditsPage'));

// Sub-pages - Lazy loaded
const RSVPManagement = lazy(() => import('./pages/RSVPManagement'));
const GuestListManager = lazy(() => import('./pages/GuestListManager'));
const Phase30AnalyticsPage = lazy(() => import('./pages/Phase30AnalyticsPage'));
const GreetingsManagement = lazy(() => import('./pages/GreetingsManagement'));
const WishesManagement = lazy(() => import('./pages/WishesManagement'));
const PostWeddingManagement = lazy(() => import('./pages/PostWeddingManagement'));
const QRCodeManagement = lazy(() => import('./pages/QRCodeManagement'));
const AuditLogsPage = lazy(() => import('./pages/AuditLogsPage'));
const ReferralsCreditsPage = lazy(() => import('./pages/ReferralsCreditsPage'));
const ThemeSettingsPage = lazy(() => import('./pages/ThemeSettingsPage'));

// Premium features - Lazy loaded
const LivePhotoWall = lazy(() => import('./pages/LivePhotoWall'));
const LiveGalleryManagement = lazy(() => import('./pages/LiveGalleryManagement'));
const AIStudio = lazy(() => import('./pages/AIStudio'));
const WhatsAppManager = lazy(() => import('./pages/WhatsAppManager'));
const DigitalShagunSettings = lazy(() => import('./pages/DigitalShagunSettings'));
const GiftRegistryEditor = lazy(() => import('./pages/GiftRegistryEditor'));
const GalleryManager = lazy(() => import('./pages/GalleryManager'));
const PhotographerLiveMode = lazy(() => import('./pages/PhotographerLiveMode'));

// Monetization - Lazy loaded
const PhotographerDetail = lazy(() => import('./pages/PhotographerDetail'));

// User flows - Lazy loaded
const UserDashboard = lazy(() => import('./pages/UserDashboard'));
const UserProfile = lazy(() => import('./pages/UserProfile'));
const UserDesignPicker = lazy(() => import('./pages/UserDesignPicker'));
const UserInvitationForm = lazy(() => import('./pages/UserInvitationForm'));
const PurchaseOptionsWizard = lazy(() => import('./pages/PurchaseOptionsWizard'));
const PublicPricingPage = lazy(() => import('./pages/PublicPricingPage'));

import './App.css';
import { AnimationProvider } from './components/animations';
import ScrollToTop from './components/ScrollToTop';
import RouteCleanup from './components/perf/RouteCleanup';

function App() {
  React.useEffect(() => {
    // Apply luxury cinematic theme globally to all pages
    document.body.classList.add('luxe', 'luxe-grain', 'luxe-vignette');
    
    // CRITICAL: Ensure body can scroll - only on mobile
    if (window.innerWidth <= 1024) {
      document.body.style.webkitOverflowScrolling = 'touch';
    }
    
    return () => {
      document.body.classList.remove('luxe', 'luxe-grain', 'luxe-vignette');
      document.body.style.webkitOverflowScrolling = '';
    };
  }, []);

  return (
    <ErrorBoundary>
      <HelmetProvider>
        <AuthProvider>
          <UserAuthProvider>
          <AnimationProvider>
            <div className="App">
              <BrowserRouter>
              <ScrollToTop />
              <RouteCleanup />
              <Suspense fallback={<LoadingFallback variant="page" />}>
              <Routes>
                {/* Public */}
                <Route path="/" element={<LandingPage />} />
                <Route path="/pricing" element={<PublicPricingPage />} />
                <Route path="/auth/callback" element={<AuthCallback />} />
                <Route path="/themes" element={<ThemeShowroom />} />
                <Route path="/themes/kerala_backwaters/gallery" element={<KeralaDesignGallery />} />
                <Route path="/themes/:themeId/gallery" element={<ThemeDesignGallery />} />
                {/* NEW: step-by-step picker — Theme → 6 events → 3 designs → fullscreen preview */}
                <Route path="/themes/:themeId/events" element={<ThemeEventPicker />} />
                <Route path="/themes/:themeId/events/:event" element={<EventDesignPicker />} />
                <Route path="/themes/:themeId/events/:event/design/:designIndex" element={<DesignFullPreview />} />
                <Route path="/themes/:themeId" element={<ThemeShowroom />} />
                <Route path="/preview/luxe" element={<LuxuryPreview />} />
                <Route path="/preview/theme/:themeId" element={<ThemeInvitationPreview />} />
                {/* 2026-09 — Sample invitation preview for non-wedding
                    categories (baby_birthday / half_saree / puberty / dhoti).
                    Optional designId pre-fills the cover photo with that
                    design's artwork. */}
                <Route path="/preview/celebration/:category" element={<CelebrationInvitationPreview />} />
                <Route path="/preview/celebration/:category/:designId" element={<CelebrationInvitationPreview />} />
                <Route path="/invite/:slug" element={<LuxuryPublicInvitation />} />
                <Route path="/invite/:slug/:eventType" element={<LuxuryPublicInvitation />} />
                {/* Phase 2A — Save the Date teaser page */}
                <Route path="/save-the-date/:slug" element={<SaveTheDatePage />} />

                {/* Couple portal */}
                <Route path="/couple/access" element={<CoupleAccess />} />
                <Route path="/couple/access/:slug" element={<CoupleAccess />} />

                {/* Super Admin */}
                <Route path="/super-admin/login" element={<SuperAdminLogin />} />
                <Route path="/super-admin/dashboard" element={<LuxurySuperAdminDashboard />} />
                <Route path="/super-admin/pricing" element={<SuperAdminPricingHub />} />
                {/* Backward-compat redirects: every legacy pricing URL → unified hub */}
                <Route path="/super-admin/credit-packs" element={<SuperAdminPricingHub />} />
                <Route path="/super-admin/credit-packs-new" element={<SuperAdminPricingHub />} />
                <Route path="/super-admin/design-pricing" element={<SuperAdminPricingHub />} />
                <Route path="/super-admin/design-pricing-new" element={<SuperAdminPricingHub />} />
                <Route path="/super-admin/plans-pricing" element={<SuperAdminPricingHub />} />
                <Route path="/super-admin/pricing-discounts" element={<SuperAdminPricingHub />} />
                <Route path="/super-admin/pricing-editor" element={<SuperAdminPricingHub />} />
                <Route path="/super-admin/credits" element={<SuperAdminPricingHub />} />
                <Route path="/super-admin/expiry-tiers" element={<SuperAdminExpiryTiers />} />

                {/* Photographer Admin */}
                <Route path="/admin/login" element={<AdminLogin />} />
                <Route path="/admin/signup" element={<AdminSignup />} />
                <Route path="/admin/dashboard" element={<LuxuryDashboard />} />
                <Route path="/admin/category-selector" element={<EventCategorySelector />} />
                <Route path="/admin/celebration/new" element={<CelebrationProfileForm />} />
                <Route path="/admin/celebration/:profileId/edit" element={<CelebrationProfileForm />} />
                <Route path="/user/celebration/new" element={<CelebrationProfileForm />} />
                <Route path="/user/celebration/:profileId/edit" element={<CelebrationProfileForm />} />
                <Route path="/admin/dashboard/trash" element={<TrashBinPage />} />

                {/* Wedding Editor (luxury wizard) */}
                <Route path="/admin/profile/new" element={<LuxuryProfileForm />} />
                <Route path="/admin/profile/:profileId/edit" element={<LuxuryProfileForm />} />
                <Route path="/admin/wedding/:weddingId/edit" element={<LuxuryProfileForm />} />

                {/* Per-event Invitation Link Wizard */}
                <Route path="/admin/profile/:profileId/invitations" element={<EventInvitationWizard />} />

                {/* Functional sub-pages (unchanged) */}
                <Route path="/admin/profile/:profileId/rsvps" element={<RSVPManagement />} />
                <Route path="/admin/profile/:profileId/guests" element={<GuestListManager />} />
                <Route path="/admin/profile/:profileId/analytics" element={<Phase30AnalyticsPage />} />
                <Route path="/admin/profile/:profileId/greetings" element={<GreetingsManagement />} />
                <Route path="/admin/profile/:profileId/wishes" element={<WishesManagement />} />
                <Route path="/admin/profile/:profileId/post-wedding" element={<PostWeddingManagement />} />
                <Route path="/admin/profile/:profileId/qr-codes" element={<QRCodeManagement />} />
                <Route path="/admin/profile/:profileId/referrals" element={<ReferralsCreditsPage />} />
                <Route path="/admin/profile/:profileId/theme-settings" element={<ThemeSettingsPage />} />
                <Route path="/admin/audit-logs" element={<AuditLogsPage />} />

                {/* Phase 38 — premium features */}
                <Route path="/admin/profile/:profileId/ai-studio" element={<AIStudio />} />
                <Route path="/admin/profile/:profileId/live-gallery" element={<LiveGalleryManagement />} />
                <Route path="/admin/profile/:profileId/whatsapp" element={<WhatsAppManager />} />
                <Route path="/admin/profile/:profileId/shagun" element={<DigitalShagunSettings />} />
                <Route path="/admin/profile/:profileId/gifts" element={<GiftRegistryEditor />} />
                <Route path="/admin/profile/:profileId/gallery" element={<GalleryManager />} />
                <Route path="/live/:profileId" element={<PhotographerLiveMode />} />
                <Route path="/invite/:slug/live-gallery" element={<LivePhotoWall />} />

                {/* Monetization (legacy duplicates removed — now point to unified /super-admin/pricing) */}
                <Route path="/super-admin/gift-codes" element={<SuperAdminGiftCodes />} />
                <Route path="/super-admin/photographers/:adminId" element={<PhotographerDetail />} />
                <Route path="/admin/credits/top-up" element={<AccountCreditsPage />} />
                <Route path="/account/credits" element={<AccountCreditsPage />} />
                <Route path="/credits" element={<AccountCreditsPage />} />
                <Route path="/purchase" element={<PurchaseFlowPage />} />

                {/* Normal-user (wedding-couple) flows */}
                <Route path="/user/dashboard" element={<UserDashboard />} />
                <Route path="/user/profile" element={<UserProfile />} />
                <Route path="/user/buy-credits" element={<AccountCreditsPage />} />
                <Route path="/user/create-invitation" element={<UserDesignPicker />} />
                <Route path="/user/create-invitation/:themeId/:event/:designId" element={<UserInvitationForm />} />
                <Route path="/user/buy-theme/:themeId" element={<PurchaseOptionsWizard />} />
                <Route path="/user/buy-design/:themeId/:event/:designId" element={<PurchaseOptionsWizard />} />
                <Route path="/user/buy-celebration/:category/:designId" element={<CelebrationPurchaseWizard />} />
              </Routes>
              </Suspense>
              </BrowserRouter>
            </div>
          </AnimationProvider>
          </UserAuthProvider>
        </AuthProvider>
      </HelmetProvider>
    </ErrorBoundary>
  );
}

export default App;
