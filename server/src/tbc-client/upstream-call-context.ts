export interface UpstreamCallContext {
  readonly gatewayRequestId: string;
  readonly psuIpAddress?: string;
}

export interface UpstreamAuthorisation {
  readonly consentId: string;
  readonly accessToken: string;
}

export type UpstreamBookingStatus = 'booked' | 'pending' | 'both';

export interface UpstreamTransactionQuery {
  readonly dateFrom?: string;
  readonly dateTo?: string;
  readonly bookingStatus?: UpstreamBookingStatus;
}
