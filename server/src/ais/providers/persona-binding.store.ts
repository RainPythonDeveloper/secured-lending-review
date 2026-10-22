import { Injectable } from '@nestjs/common';

// Remembers which organizer dataset customer a consent was created for (PSU-ID at consent creation).
@Injectable()
export class PersonaBindingStore {
  private readonly customerIdByConsentId = new Map<string, string>();

  bind(consentId: string, customerId: string): void {
    this.customerIdByConsentId.set(consentId, customerId);
  }

  findCustomerId(consentId: string): string | undefined {
    return this.customerIdByConsentId.get(consentId);
  }

  unbind(consentId: string): void {
    this.customerIdByConsentId.delete(consentId);
  }
}
