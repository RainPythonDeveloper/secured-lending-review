import { Module } from '@nestjs/common';
import { GatewayConfig } from '../config/gateway-config.js';
import { OrganizerDataset } from './organizer-dataset.js';
import { loadOrganizerDataset } from './organizer-dataset.loader.js';

@Module({
  providers: [
    {
      provide: OrganizerDataset,
      useFactory: (config: GatewayConfig): Promise<OrganizerDataset> =>
        loadOrganizerDataset(config.dataset.xlsxPath),
      inject: [GatewayConfig],
    },
  ],
  exports: [OrganizerDataset],
})
export class OrganizerDatasetModule {}
