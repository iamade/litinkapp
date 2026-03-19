export const CREDITS_REFRESH_EVENT = "credits:refresh";
export const INSUFFICIENT_CREDITS_EVENT = "credits:insufficient";

export interface CreditGrant {
  id?: string;
  credits_granted?: number;
  amount?: number;
  [key: string]: unknown;
}

export interface CreditBalanceResponse {
  total_credits: number;
  grants?: CreditGrant[];
}

export interface InsufficientCreditsEventDetail {
  balance: number;
  required: number;
  detail?: string;
  endpoint?: string;
}

export function dispatchCreditsRefresh() {
  window.dispatchEvent(new Event(CREDITS_REFRESH_EVENT));
}

export function dispatchInsufficientCredits(detail: InsufficientCreditsEventDetail) {
  window.dispatchEvent(new CustomEvent<InsufficientCreditsEventDetail>(INSUFFICIENT_CREDITS_EVENT, { detail }));
}
