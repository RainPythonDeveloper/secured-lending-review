import {
  Body,
  Controller,
  Delete,
  Get,
  HttpCode,
  HttpStatus,
  Param,
  Post,
} from '@nestjs/common';
import { ApiHeader, ApiOperation, ApiTags } from '@nestjs/swagger';
import type { SourcedResponse } from '../../common/data-source/data-source.js';
import { OPEN_BANKING_HEADER } from '../../common/open-banking-headers.js';
import {
  PsuIdHeader,
  UpstreamContext,
} from '../../common/request-context/request-context.decorators.js';
import {
  ApiDataSourceResponseHeader,
  ApiProblemResponses,
  ApiPsuIpAddressHeader,
  ApiRequestIdHeader,
} from '../../common/swagger/api-gateway.decorators.js';
import type { UpstreamCallContext } from '../../tbc-client/upstream-call-context.js';
import { ConsentsService } from './consents.service.js';
import { ConsentDetailsResponseDto } from './dto/consent-details-response.dto.js';
import { ConsentIdParamDto } from './dto/consent-id-param.dto.js';
import { ConsentStatusResponseDto } from './dto/consent-status-response.dto.js';
import { CreateConsentRequestDto } from './dto/create-consent-request.dto.js';
import { CreateConsentResponseDto } from './dto/create-consent-response.dto.js';

@ApiTags('AIS consents')
@ApiPsuIpAddressHeader()
@ApiRequestIdHeader()
@ApiProblemResponses(
  HttpStatus.BAD_REQUEST,
  HttpStatus.UNAUTHORIZED,
  HttpStatus.FORBIDDEN,
  HttpStatus.NOT_FOUND,
  HttpStatus.BAD_GATEWAY,
  HttpStatus.GATEWAY_TIMEOUT,
)
@Controller('v1/consents')
export class ConsentsController {
  constructor(private readonly consentsService: ConsentsService) {}

  @Post()
  @HttpCode(HttpStatus.CREATED)
  @ApiOperation({
    summary: 'Create an AIS consent at the bank and start its authorisation',
  })
  @ApiHeader({
    name: OPEN_BANKING_HEADER.PSU_ID,
    required: false,
    description:
      'Organizer dataset customer id (CUS-…) whose synthetic accounts this consent serves. ' +
      'Without it, or for an id that is not in the dataset, the consent serves TBC sandbox data.',
    schema: { type: 'string' },
  })
  @ApiDataSourceResponseHeader({
    status: HttpStatus.CREATED,
    description:
      'Consent received by the bank. Open _links.scaRedirect.href in the PSU browser to authorise it.',
    type: CreateConsentResponseDto,
  })
  createConsent(
    @Body() request: CreateConsentRequestDto,
    @PsuIdHeader() psuId: string | undefined,
    @UpstreamContext() context: UpstreamCallContext,
  ): Promise<SourcedResponse<CreateConsentResponseDto>> {
    return this.consentsService.createConsent(request, psuId, context);
  }

  @Get(':consentId')
  @ApiOperation({ summary: 'Read the consent as stored at the bank' })
  @ApiDataSourceResponseHeader({
    status: HttpStatus.OK,
    description: 'Consent details.',
    type: ConsentDetailsResponseDto,
  })
  getConsent(
    @Param() { consentId }: ConsentIdParamDto,
    @UpstreamContext() context: UpstreamCallContext,
  ): Promise<SourcedResponse<ConsentDetailsResponseDto>> {
    return this.consentsService.getConsent(consentId, context);
  }

  @Get(':consentId/status')
  @ApiOperation({ summary: 'Read the consent status at the bank' })
  @ApiDataSourceResponseHeader({
    status: HttpStatus.OK,
    description: 'Consent status.',
    type: ConsentStatusResponseDto,
  })
  getConsentStatus(
    @Param() { consentId }: ConsentIdParamDto,
    @UpstreamContext() context: UpstreamCallContext,
  ): Promise<SourcedResponse<ConsentStatusResponseDto>> {
    return this.consentsService.getConsentStatus(consentId, context);
  }

  @Delete(':consentId')
  @HttpCode(HttpStatus.NO_CONTENT)
  @ApiOperation({
    summary: 'Terminate the consent at the bank',
    description:
      'Afterwards the gateway forgets the tokens and the persona binding of the consent.',
  })
  @ApiDataSourceResponseHeader({
    status: HttpStatus.NO_CONTENT,
    description: 'Consent terminated.',
  })
  deleteConsent(
    @Param() { consentId }: ConsentIdParamDto,
    @UpstreamContext() context: UpstreamCallContext,
  ): Promise<SourcedResponse<undefined>> {
    return this.consentsService.deleteConsent(consentId, context);
  }
}
