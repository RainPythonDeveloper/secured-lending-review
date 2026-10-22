export const TBC_SANDBOX_DATA_SOURCE = 'tbc-sandbox';
export const ORGANIZER_DATASET_DATA_SOURCE = 'organizer-dataset';
export const DATA_SOURCES = [
  TBC_SANDBOX_DATA_SOURCE,
  ORGANIZER_DATASET_DATA_SOURCE,
] as const;
export const DATA_SOURCE_HEADER = 'X-Data-Source';

export type DataSource = (typeof DATA_SOURCES)[number];

// Services return this wrapper; DataSourceHeaderInterceptor turns it into the X-Data-Source header and the body.
export class SourcedResponse<Body> {
  constructor(
    readonly dataSource: DataSource,
    readonly body: Body,
  ) {}
}
