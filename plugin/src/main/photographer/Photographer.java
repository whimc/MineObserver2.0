package edu.whimc.photographer;

import com.corundumstudio.socketio.Configuration;
import com.corundumstudio.socketio.SocketIOClient;
import com.corundumstudio.socketio.SocketIOServer;
import edu.whimc.observations.Observations;
import edu.whimc.observations.models.Observation;
import edu.whimc.photographer.socket.Response;
import java.util.LinkedList;
import java.util.Optional;
import java.util.Queue;
import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.command.PluginCommand;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;

public final class Photographer extends JavaPlugin {

    private final Queue<Observation> observationQueue = new LinkedList<>();

    private SocketIOServer socketServer;
    private Observations observationsPlugin;

    @Override
    public void onEnable() {
        super.saveDefaultConfig();

        this.observationsPlugin = (Observations) getServer().getPluginManager().getPlugin("WHIMC-Observations");

        Configuration config = new Configuration();
        config.setHostname(super.getConfig().getString("websocket.host"));
        config.setPort(super.getConfig().getInt("websocket.port"));

        this.socketServer = new SocketIOServer(config);
        this.socketServer.addConnectListener(client -> {
            UUID uuid = UUID.randomUUID();
            client.set("uuid", uuid);
            client.sendEvent("uuid", uuid);
            this.getLogger().info("connected to " + client.getRemoteAddress() + " [" + uuid + "]");
        });

        this.socketServer.addDisconnectListener(
                client -> CameraOperator.getCameraOperator(client.get("uuid")).ifPresent(co -> {
                    this.getLogger().info("Disconnected from " + co.getClientAddress() +
                            " [" + co.getClientUuid() + "]");
                    Bukkit.getScheduler().runTask(this, () -> co.unregister());
                }));

        socketServer.addEventListener("test", String.class, (client, message, ackRequest) ->
                Bukkit.broadcastMessage(client.getRemoteAddress() + " [" + client.get("uuid") + "]: " + message)
        );

        socketServer.addEventListener("screenshot_response", Response.class, (client, response, ackRequest) -> {
            CameraOperator.getCameraOperator(response.getClientUuid()).ifPresent(co -> co.setCurrentObservation(null));

            this.getLogger().info("Observation ID: " + response.getObservationId());
            this.getLogger().info("Feedback: " + response.getFeedback());
            this.getLogger().info("Generated caption: " + response.getGeneratedCaption());
            this.getLogger().info("Score: " + response.getScore());

            Player player = Bukkit.getPlayer(response.getPlayerName());
            if (player == null) {
                return;
            }

            Utils.msg(player, "&m                                                                                 ");
            Utils.msg(player, "&b&lYour observation has been analyzed!");
            Utils.msg(player, "");
            Utils.msg(player, "&e&lFEEDBACK:");
            Utils.msg(player, "    &6" + response.getFeedback());
            Utils.msg(player, "");
            Utils.msg(player, "&e&lGENERATED:");
            Utils.msg(player, "    &6" + response.getGeneratedCaption());
            Utils.msg(player, "");
            Utils.msg(player, "&m                                                                                 ");
        });

        socketServer.addEventListener("screenshot_failed", int.class, (client, failed_id, ackRequest) -> {
            // Re-add the event to the queue if the screenshot failed

            CameraOperator.getCameraOperator(client.get("uuid")).ifPresent(co -> {
                Observation observation = Observation.getObservation(failed_id);
                if (co.getCurrentObservation().getId() == failed_id) {
                    co.setCurrentObservation(null);
                }
                this.observationQueue.add(observation);
                this.getLogger().warning("Observation " + observation.getId() +
                        " could not be screenshotted. Re-adding to queue");
            });
        });

        this.socketServer.start();

        // Queue up some events
        Bukkit.getScheduler().scheduleSyncRepeatingTask(this, () -> {
            if (this.observationQueue.isEmpty()) {
                return;
            }
            CameraOperator.getAvailableOperator().ifPresent(co -> co.photograph(this.observationQueue.poll()));
        }, 20, 20);

        getServer().getPluginManager().registerEvents(new Listeners(this), this);

        PluginCommand cmd = getCommand("photographer");
        PhotographerCommand photographerCommand = new PhotographerCommand(this);
        cmd.setExecutor(photographerCommand);
        cmd.setTabCompleter(photographerCommand);
    }

    @Override
    public void onDisable() {
        CameraOperator.getAllCameraOperators().forEach(CameraOperator::unregister);
        this.socketServer.stop();
    }

    public void queueObservationPhotograph(Observation observation) {
        this.observationQueue.add(observation);
    }

    public Queue<Observation> getObservationQueue() {
        return this.observationQueue;
    }

    public SocketIOServer getSocketServer() {
        return this.socketServer;
    }

    public Observations getObservationsPlugin() {
        return this.observationsPlugin;
    }

    public Optional<SocketIOClient> getClient(UUID clientUuid) {
        return this.socketServer.getAllClients().stream()
                .filter(c -> c.get("uuid").equals(clientUuid))
                .findFirst();
    }

}
