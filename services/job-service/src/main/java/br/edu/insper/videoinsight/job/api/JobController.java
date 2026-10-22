package br.edu.insper.videoinsight.job.api;

import br.edu.insper.videoinsight.job.application.JobResultView;
import br.edu.insper.videoinsight.job.application.JobService;
import br.edu.insper.videoinsight.job.storage.PresignedUrl;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/** Implementa {@code contracts/openapi/job-service.yaml}. O serviço valida JWT Auth0 e restringe recursos ao proprietário. */
@RestController
@RequestMapping("/api/v1")
public class JobController {
    private final JobService jobService;

    public JobController(JobService jobService) {
        this.jobService = jobService;
    }

    @PostMapping("/videos/{videoId}/jobs")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public JobResponse createJob(
            @PathVariable UUID videoId,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @Valid @RequestBody CreateJobRequest request) {
        return JobResponse.from(jobService.createJob(videoId, idempotencyKey, request.operations()));
    }

    @GetMapping("/videos/{videoId}/jobs")
    public JobPageResponse listJobs(
            @PathVariable UUID videoId,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int limit,
            @RequestParam(required = false) String cursor) {
        return JobPageResponse.from(jobService.listJobs(videoId, limit, cursor));
    }

    @GetMapping("/jobs/{jobId}")
    public JobResponse getJob(@PathVariable UUID jobId) {
        return JobResponse.from(jobService.getJob(jobId));
    }

    @PostMapping("/jobs/{jobId}/cancel")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public JobResponse cancelJob(@PathVariable UUID jobId) {
        return JobResponse.from(jobService.cancelJob(jobId));
    }

    @PostMapping("/jobs/{jobId}/retry")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public JobResponse retryJob(@PathVariable UUID jobId) {
        return JobResponse.from(jobService.retryJob(jobId));
    }

    @GetMapping("/jobs/{jobId}/result")
    public JobResultView getJobResult(@PathVariable UUID jobId) {
        return jobService.getResult(jobId);
    }

    @GetMapping("/jobs/{jobId}/transcript")
    public PresignedUrl exportTranscript(@PathVariable UUID jobId, @RequestParam String format) {
        return jobService.exportTranscript(jobId, format);
    }
}
