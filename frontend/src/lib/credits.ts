export const CREDITS_REFRESH_EVENT = "credits:refresh";

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

export function dispatchCreditsRefresh() {
  window.dispatchEvent(new Event(CREDITS_REFRESH_EVENT));
}
