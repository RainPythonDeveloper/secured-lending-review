import { Logger } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';
import { setupSwagger } from './common/swagger/setup-swagger.js';
import { GatewayConfig } from './config/gateway-config.js';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule);
  app.enableShutdownHooks();
  setupSwagger(app);
  const { port } = app.get(GatewayConfig);
  await app.listen(port);
  new Logger('Bootstrap').log(`Gateway listening on port ${port}`);
}

void bootstrap();
