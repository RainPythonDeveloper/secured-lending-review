import { Controller, Get, HttpStatus, Query } from '@nestjs/common';
import { ApiOkResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import { UpstreamContext } from '../common/request-context/request-context.decorators.js';
import { ApiProblemResponses } from '../common/swagger/api-gateway.decorators.js';
import type { UpstreamCallContext } from '../tbc-client/upstream-call-context.js';
import { OAuthCallbackQueryDto } from './dto/oauth-callback-query.dto.js';
import {
  FINALISED_SCA_STATUS,
  OAuthCallbackResponseDto,
} from './dto/oauth-callback-response.dto.js';
import { OAuthService } from './oauth.service.js';

@ApiTags('OAuth')
@Controller('oauth')
export class OAuthController {
  constructor(private readonly oauthService: OAuthService) {}

  @Get('callback')
  @ApiOperation({
    summary: 'Complete the bank authorisation of a consent',
    description:
      'Redirect target of the bank consent screen. Exchanges the authorisation code for tokens ' +
      '(authorization code flow with PKCE); the tokens stay inside the gateway.',
  })
  @ApiOkResponse({ type: OAuthCallbackResponseDto })
  @ApiProblemResponses(
    HttpStatus.BAD_REQUEST,
    HttpStatus.FORBIDDEN,
    HttpStatus.BAD_GATEWAY,
    HttpStatus.GATEWAY_TIMEOUT,
  )
  async completeAuthorisation(
    @Query() query: OAuthCallbackQueryDto,
    @UpstreamContext() context: UpstreamCallContext,
  ): Promise<OAuthCallbackResponseDto> {
    const { consentId } = await this.oauthService.completeAuthorisation(
      query,
      context,
    );
    return { consentId, scaStatus: FINALISED_SCA_STATUS };
  }
}
