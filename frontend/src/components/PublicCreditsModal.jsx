// Thin re-export so multiple pages can use the modal without duplicating it.
// PublicCreditsModal itself lives in LandingPage.jsx alongside its Razorpay
// flow and credit-pack fetching logic; this wrapper just makes it importable
// from a stable module path.
export { PublicCreditsModal as default } from '../pages/LandingPage';
