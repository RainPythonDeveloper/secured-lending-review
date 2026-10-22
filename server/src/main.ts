import { NestFactory } from '@nestjs/core';
import { Logger } from '@nestjs/common';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { AppModule, ObserveInstrument } from './app.module.js';

async function bootstrap() {
  const logger = new Logger('Bootstrap');

  const app = await NestFactory.create(AppModule, {
    instrument: ObserveInstrument,
  });

  // Настройка Swagger (если вы не настраивали его отдельно в другом месте)
  const config = new DocumentBuilder()
    .setTitle('TBC Bank Mock Open Banking API')
    .setDescription('API documentation for Accounts Information Service')
    .setVersion('0.8')
    .addBearerAuth()
    .build();
  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api/docs', app, document);

  const port = process.env.PORT ?? 3000;
  await app.listen(port);

  // Вывод красивых логов с адресами для проверки
  logger.log(`🚀 Application is running on: http://localhost:${port}`);
  logger.log(`📄 Swagger documentation is ready at: http://localhost:${port}/api/docs`);
}

bootstrap();