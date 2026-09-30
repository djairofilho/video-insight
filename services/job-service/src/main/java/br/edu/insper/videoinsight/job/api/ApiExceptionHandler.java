package br.edu.insper.videoinsight.job.api;

import br.edu.insper.videoinsight.job.application.ApiException;
import br.edu.insper.videoinsight.job.domain.InvalidJobStateException;
import br.edu.insper.videoinsight.job.video.VideoServiceUnavailableException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingRequestHeaderException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

/** Converte qualquer erro no formato {@code Error} do contrato. */
@RestControllerAdvice
public class ApiExceptionHandler {
    private static final Logger log = LoggerFactory.getLogger(ApiExceptionHandler.class);

    @ExceptionHandler(ApiException.class)
    ResponseEntity<ErrorResponse> handleApiException(ApiException exception) {
        return error(exception.getStatus(), exception.getCode(), exception.getMessage());
    }

    @ExceptionHandler(InvalidJobStateException.class)
    ResponseEntity<ErrorResponse> handleInvalidState(InvalidJobStateException exception) {
        return error(HttpStatus.CONFLICT, "INVALID_JOB_STATE", exception.getMessage());
    }

    @ExceptionHandler(VideoServiceUnavailableException.class)
    ResponseEntity<ErrorResponse> handleVideoServiceUnavailable(VideoServiceUnavailableException exception) {
        log.warn("Falha ao consultar o Video Service", exception);
        return error(HttpStatus.SERVICE_UNAVAILABLE, "VIDEO_SERVICE_UNAVAILABLE", exception.getMessage());
    }

    @ExceptionHandler({
            MethodArgumentNotValidException.class,
            HandlerMethodValidationException.class,
            HttpMessageNotReadableException.class,
            MissingRequestHeaderException.class,
            MissingServletRequestParameterException.class,
            MethodArgumentTypeMismatchException.class
    })
    ResponseEntity<ErrorResponse> handleBadRequest(Exception exception) {
        return error(HttpStatus.BAD_REQUEST, "INVALID_REQUEST", "Requisição inválida: " + summary(exception));
    }

    @ExceptionHandler(NoResourceFoundException.class)
    ResponseEntity<ErrorResponse> handleNoResource(NoResourceFoundException exception) {
        return error(HttpStatus.NOT_FOUND, "NOT_FOUND", "Recurso não encontrado.");
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    ResponseEntity<ErrorResponse> handleMethodNotSupported(HttpRequestMethodNotSupportedException exception) {
        return error(HttpStatus.METHOD_NOT_ALLOWED, "METHOD_NOT_ALLOWED", exception.getMessage());
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<ErrorResponse> handleUnexpected(Exception exception) {
        log.error("Erro inesperado", exception);
        return error(HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Erro interno.");
    }

    private static ResponseEntity<ErrorResponse> error(HttpStatus status, String code, String message) {
        return ResponseEntity.status(status).body(ErrorResponse.of(code, message));
    }

    private static String summary(Exception exception) {
        if (exception instanceof MethodArgumentNotValidException invalid) {
            return invalid.getBindingResult().getFieldErrors().stream()
                    .map(error -> error.getField() + " " + error.getDefaultMessage())
                    .findFirst()
                    .orElse("corpo inválido");
        }
        if (exception instanceof MissingRequestHeaderException missing) {
            return "header " + missing.getHeaderName() + " ausente";
        }
        if (exception instanceof MissingServletRequestParameterException missing) {
            return "parâmetro " + missing.getParameterName() + " ausente";
        }
        if (exception instanceof MethodArgumentTypeMismatchException mismatch) {
            return "valor inválido para " + mismatch.getName();
        }
        return "corpo ou parâmetros inválidos";
    }
}
