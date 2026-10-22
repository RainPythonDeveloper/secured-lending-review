import type { INestApplication } from '@nestjs/common';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';

export const SWAGGER_UI_PATH = 'api/docs';

const API_TITLE = 'Virtual Field Visit - Open Banking AIS gateway';
const API_DESCRIPTION = [
  'Account Information Service gateway to the TBC Bank mock Open Banking sandbox ' +
    '(Georgian standard based on Berlin Group NextGenPSD2).',
  'All data served here is synthetic. Account data comes either from the TBC mock sandbox ' +
    'or from the hackathon organizer dataset; the X-Data-Source response header ' +
    '(tbc-sandbox or organizer-dataset) names the source of the account data served under a consent.',
  'Errors are returned as application/problem+json. Every response carries an X-Request-ID header.',
  'Callers are not authenticated: a Consent-ID acts as a capability for the data of that consent, ' +
    'so run the gateway on localhost or a private network only.',
].join('\n\n');

// Must run before app.init(), otherwise the 404 handler shadows the documentation routes.
export function setupSwagger(app: INestApplication): void {
  const documentConfig = new DocumentBuilder()
    .setTitle(API_TITLE)
    .setDescription(API_DESCRIPTION)
    .build();
  SwaggerModule.setup(SWAGGER_UI_PATH, app, () =>
    SwaggerModule.createDocument(app, documentConfig),
  );
}
