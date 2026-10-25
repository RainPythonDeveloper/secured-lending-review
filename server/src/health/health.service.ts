import { Injectable } from '@nestjs/common';
import { HealthResponseDto } from './dto/health-response.dto.js';

@Injectable()
export class HealthService {
  getStatus(): HealthResponseDto {
    return { status: 'ok' };
  }
}
