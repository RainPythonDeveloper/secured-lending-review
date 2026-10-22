import { Logger } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { AppModule } from './app.module.js';
import { GatewayConfig } from './config/gateway-config.js';

const SWAGGER_UI_PATH = 'api/docs';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule);
  app.enableShutdownHooks();
  const documentConfig = new DocumentBuilder()
    .setTitle('Open Banking AIS gateway')
    .build();
  SwaggerModule.setup(SWAGGER_UI_PATH, app, () =>
    SwaggerModule.createDocument(app, documentConfig),
  );
  const { port } = app.get(GatewayConfig);
  await app.listen(port);
  new Logger('Bootstrap').log(`Gateway listening on port ${port}`);
}

void bootstrap();
