### Loads exercise videos information from production and posts it to the
### specified test (defaults to localhost) server.

DOMAIN = ARGV.length > 0 ? ARGV[0].gsub(/^\d+$/, "http://127.0.0.1:\\0") : "http://127.0.0.1:8080"

###
require 'net/http'
begin
  require 'rubygems'
  require 'mechanize'
  require 'json'
rescue LoadError => e
  puts "Run \"sudo gem install mechanize json\" to install the required gems."
  exit
end

@agent = Mechanize.new
@agent.redirect_ok = false

# get the exercise list from the website
exercise_endpoint = URI.parse("http://www.khanacademy.org/api/v1/exercises")
resp = Net::HTTP.get_response(exercise_endpoint)
@exercises = JSON.parse(resp.body)

@agent.get(DOMAIN + '/_ah/login?email=test%40example.com&admin=True&action=Login&continue=http%3A%2F%2F127.0.0.1%3A8082%2F')

@exercises.each_with_index do |ex, exi|
  name = ex["name"]
  summative = ex["summative"]
  h_position = ex["h_position"]
  v_position = ex["v_position"]
  short_display_name = ex["short_display_name"]
  prerequisites = ex["prerequisites"]
  covers = ex["covers"]

  params = {
    "name" => name,
    "summative" => summative ? "1" : "",
    "h_position" => h_position,
    "v_position" => v_position,
    "short_display_name" => short_display_name,
    "live" => "1",
  }

  prerequisites.each_with_index do |prereq, i|
    params["prereq-#{i}"] = prereq
  end

  covers.each_with_index do |cover, i|
    params["cover-#{i}"] = cover
  end

  # Exercise-video associations
  exercise_video_endpoint = URI.parse("http://www.khanacademy.org/api/v1/exercises/#{name}/videos")
  resp = Net::HTTP.get_response(exercise_video_endpoint)
  @exercise_videos = JSON.parse(resp.body)

  @exercise_videos.each_with_index do |exv, exvi|
    params["video-#{exvi}-readable"] = exv["readable_id"]
  end

  qs = Mechanize::Util.build_query_string(params)
  begin
    # this will toss an exception sometimes
    @page = @agent.get(DOMAIN + "/updateexercise?#{qs}")
    puts " %3d of #{@exercises.length}: #{name} (#{@exercise_videos.length} videos)" % (exi + 1)
  rescue
    puts "! Problem with posting #{name}"
  end

end
