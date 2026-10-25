export class OrganizerDatasetFormatError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'OrganizerDatasetFormatError';
  }
}

export class OrganizerDatasetIntegrityError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'OrganizerDatasetIntegrityError';
  }
}
